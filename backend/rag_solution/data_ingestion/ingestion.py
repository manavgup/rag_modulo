"""Document ingestion pipeline.

This module provides functionality for ingesting documents from various sources
and storing them in vector databases for retrieval.
"""

import logging
import multiprocessing
from typing import Any

from core.config import Settings, get_settings
from core.custom_exceptions import DocumentStorageError
from core.identity_service import IdentityService
from rag_solution.data_ingestion.document_processor import DocumentProcessor
from rag_solution.file_management.database import create_session_factory
from rag_solution.generation.providers.factory import LLMProviderFactory
from vectordbs.data_types import Document
from vectordbs.vector_store import VectorStore

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Remove module-level constants - use dependency injection instead
MAX_RETRIES = 3  # Maximum number of retries for storing a document


class DocumentStore:
    """Document store for managing document ingestion and storage.

    This class handles the complete pipeline from document processing
    to vector storage, providing a unified interface for document management.
    """

    def __init__(
        self: Any, vector_store: VectorStore, collection_name: str, settings: Settings = get_settings()
    ) -> None:
        """Initialize document store with dependency injection."""
        self.settings = settings
        self.vector_store = vector_store
        self.collection_name = collection_name
        self.documents: list[Document] = []
        self._embedding_provider = None  # Cache provider instance

    def _get_embedding_provider(self):
        """Get or create cached embedding provider instance."""
        if self._embedding_provider is None:
            logger.info("Creating new embedding provider instance")
            session_factory = create_session_factory()
            db = session_factory()
            try:
                factory = LLMProviderFactory(db)
                logger.info("LLMProviderFactory created")

                self._embedding_provider = factory.get_provider("watsonx")
                logger.info("Created cached embedding provider instance: %s", type(self._embedding_provider))

                # Test if the provider has an embeddings client
                if hasattr(self._embedding_provider, "embeddings_client"):
                    logger.info(
                        "Provider has embeddings_client: %s", self._embedding_provider.embeddings_client is not None
                    )
                else:
                    logger.warning("Provider does not have embeddings_client attribute")

            except Exception as e:
                logger.error("Error creating embedding provider: %s", e, exc_info=True)
                raise
            finally:
                db.close()
        else:
            logger.info("Using cached embedding provider instance")

        return self._embedding_provider

    def _embed_documents_batch(self, documents: list[Document]) -> list[Document]:
        """Embed all chunks from all documents in a single batch operation."""
        if not documents:
            return documents

        # Collect all text chunks from all documents
        all_texts = []
        chunk_mapping = []  # Track which chunk belongs to which document

        for doc_idx, document in enumerate(documents):
            for chunk_idx, chunk in enumerate(document.chunks):
                all_texts.append(chunk.text)
                chunk_mapping.append((doc_idx, chunk_idx))

        # Single embedding call for all texts
        if all_texts:
            logger.info("Generating embeddings for %d chunks across %d documents", len(all_texts), len(documents))
            try:
                provider = self._get_embedding_provider()
                logger.info("Provider retrieved: %s", type(provider))

                all_embeddings = provider.get_embeddings(all_texts)

                logger.info("Received %d embeddings from provider", len(all_embeddings))

                if not all_embeddings:
                    logger.error("No embeddings returned from provider!")
                    raise ValueError("No embeddings returned from provider")

                # DIMENSION MISMATCH DEBUG: Check all embedding dimensions
                logger.info("=" * 80)
                logger.info("DIMENSION DEBUG (INGESTION): Checking %d embeddings from provider", len(all_embeddings))

                if all_embeddings:
                    first_dim = len(all_embeddings[0]) if all_embeddings[0] else 0
                    logger.info("DIMENSION DEBUG (INGESTION): First embedding dimension: %d", first_dim)
                    logger.info("DIMENSION DEBUG (INGESTION): First embedding type: %s", type(all_embeddings[0]))

                    # Check if all embeddings have consistent dimensions
                    dimension_counts = {}
                    for idx, emb in enumerate(all_embeddings):
                        if emb is None:
                            logger.error("DIMENSION DEBUG (INGESTION): Embedding %d is None!", idx)
                            dimension_counts["None"] = dimension_counts.get("None", 0) + 1
                        elif isinstance(emb, list):
                            dim = len(emb)
                            dimension_counts[dim] = dimension_counts.get(dim, 0) + 1
                            if dim != first_dim:
                                logger.error(
                                    "DIMENSION DEBUG (INGESTION): Embedding %d has different dimension: %d (expected %d)",
                                    idx,
                                    dim,
                                    first_dim,
                                )
                        else:
                            logger.error(
                                "DIMENSION DEBUG (INGESTION): Embedding %d is not a list! Type: %s", idx, type(emb)
                            )
                            dimension_counts[f"Type:{type(emb).__name__}"] = (
                                dimension_counts.get(f"Type:{type(emb).__name__}", 0) + 1
                            )

                    logger.info("DIMENSION DEBUG (INGESTION): Dimension distribution: %s", dimension_counts)

                    if len(dimension_counts) > 1:
                        logger.error("DIMENSION DEBUG (INGESTION): ⚠️ INCONSISTENT DIMENSIONS DETECTED!")
                        logger.error(
                            "DIMENSION DEBUG (INGESTION): Expected all embeddings to have dimension %d", first_dim
                        )
                    else:
                        logger.info(
                            "DIMENSION DEBUG (INGESTION): ✓ All embeddings have consistent dimension: %d", first_dim
                        )

                logger.info("=" * 80)

                # Assign embeddings back to chunks
                for embedding_idx, (doc_idx, chunk_idx) in enumerate(chunk_mapping):
                    if embedding_idx < len(all_embeddings):
                        if all_embeddings[embedding_idx]:
                            documents[doc_idx].chunks[chunk_idx].embeddings = all_embeddings[embedding_idx]
                            logger.debug(
                                "Assigned embedding %d to document %d chunk %d", embedding_idx, doc_idx, chunk_idx
                            )
                        else:
                            logger.error("Embedding %d is empty/None!", embedding_idx)
                            raise ValueError(f"Embedding {embedding_idx} is empty/None")
                    else:
                        logger.error("No embedding available for index %d", embedding_idx)
                        raise ValueError(f"No embedding available for index {embedding_idx}")

                logger.info("Successfully embedded %d chunks", len(all_texts))

            except Exception as e:
                logger.error("Error during embedding generation: %s", e, exc_info=True)
                raise ValueError(f"Embedding generation failed: {e}") from e

        return documents

    async def load_documents(self, data_source: list[str], document_ids: list[str] | None = None) -> list[Document]:
        """Load documents from the specified data source and ingest them into the vector store.

        Args:
            data_source: List of file paths to process
            document_ids: Optional list of document IDs to use (must match data_source length)
        """
        try:
            processed_documents = await self.ingest_documents(data_source, document_ids)
            self.documents.extend(processed_documents)
            logger.info(
                "Ingested and processed %d documents into collection: %s",
                len(processed_documents),
                self.collection_name,
            )
            return processed_documents
        except Exception as e:
            logger.error("Error ingesting documents: %s", e, exc_info=True)
            raise

    async def ingest_documents(self, file_paths: list[str], document_ids: list[str] | None = None) -> list[Document]:
        """Ingest documents and store them in the vector store.

        Args:
            file_paths: List of file paths to process
            document_ids: Optional list of document IDs to use (must match file_paths length)
        """
        processed_documents: list[Document] = []

        # Validate document_ids if provided
        if document_ids is not None and len(document_ids) != len(file_paths):
            raise ValueError(
                f"document_ids length ({len(document_ids)}) must match file_paths length ({len(file_paths)})"
            )

        # Phase 1: Process all documents (structure only, no embeddings)
        with multiprocessing.Manager() as manager:
            processor = DocumentProcessor(manager, self.settings)

            for i, file_path in enumerate(file_paths):
                logger.info("Processing file: %s", file_path)
                try:
                    # Use provided document_id or generate new one
                    document_id = document_ids[i] if document_ids else IdentityService.generate_document_id()
                    logger.info("Using document_id: %s for file: %s", document_id, file_path)

                    # Process the document (without embeddings)
                    documents_iterator = processor.process_document(file_path, document_id)
                    async for document in documents_iterator:
                        processed_documents.append(document)
                except Exception as e:
                    logger.error("Error processing file %s: %s", file_path, e, exc_info=True)
                    raise e

        # Phase 2: Generate embeddings for all documents at once
        if processed_documents:
            logger.info("Generating embeddings for %d documents", len(processed_documents))
            processed_documents = self._embed_documents_batch(processed_documents)

            # Phase 3: Store all documents with embeddings
            self.store_documents_in_vector_store(processed_documents)

        return processed_documents

    def store_documents_in_vector_store(self, documents: list[Document]) -> None:
        """Store documents in the vector store."""
        try:
            logger.info("Storing documents in collection %s", self.collection_name)
            self.vector_store.add_documents(self.collection_name, documents)
            logger.info("Successfully stored documents in collection %s", self.collection_name)
        except Exception as e:
            logger.error("Error storing documents: %s", e, exc_info=True)
            raise DocumentStorageError(
                doc_id="", storage_path="", error_type="storage_failed", message=f"Error: {e}"
            ) from e

    def get_documents(self) -> list[Document]:
        """Get all documents in the document store."""
        return self.documents

    async def clear(self) -> None:
        """Clear all documents from the document store and vector store."""
        try:
            self.vector_store.delete_collection(self.collection_name)
            self.vector_store.create_collection(self.collection_name)
            self.documents.clear()
            logger.info("Cleared all documents from collection: %s", self.collection_name)
        except Exception as e:
            logger.error("Error clearing documents: %s", e, exc_info=True)
            raise
