"""Pinecone vector store implementation.

This module provides a Pinecone-based implementation of the VectorStore interface,
enabling document storage, retrieval, and search operations using Pinecone.
"""

import logging
import time
from typing import Any

from pinecone import Pinecone, ServerlessSpec

from core.config import Settings, get_settings

from .data_types import (
    CollectionConfig,
    Document,
    DocumentChunkMetadata,
    DocumentChunkWithScore,
    DocumentMetadataFilter,
    EmbeddedChunk,
    QueryResult,
    QueryWithEmbedding,
    Source,
    VectorDBResponse,
    VectorSearchRequest,
)
from .error_types import CollectionError, DocumentError, VectorStoreError
from .utils.embeddings import get_embeddings_for_vector_store
from .vector_store import VectorStore

logger = logging.getLogger(__name__)


class PineconeStore(VectorStore):
    """Pinecone implementation of the VectorStore interface.

    This class provides Pinecone-based vector storage and retrieval capabilities,
    including document management, collection operations, and similarity search.
    """

    def __init__(self, settings: Settings = get_settings()) -> None:
        # Call parent constructor for proper dependency injection
        super().__init__(settings)

        # Configure logging
        logging.basicConfig(level=getattr(self.settings, "log_level", "INFO"))

        # Initialize Pinecone client
        try:
            self.pc = Pinecone(api_key=self.settings.pinecone_api_key)
            logging.info("Connected to Pinecone")
        except Exception as e:
            logging.error("Failed to connect to Pinecone: %s", str(e))
            raise CollectionError(f"Failed to connect to Pinecone: {e}") from e

    def _create_collection_impl(self, config: CollectionConfig) -> dict[str, Any]:
        """Implementation-specific collection creation with Pydantic model.

        Args:
            config: Collection configuration (Pydantic model)

        Returns:
            dict: Creation result metadata

        Raises:
            CollectionError: If collection creation fails
        """
        try:
            # Validate collection config against settings
            self._validate_collection_config(config)

            # Check if index already exists
            if config.collection_name in [index.name for index in self.pc.list_indexes()]:
                logging.info("Collection '%s' already exists", config.collection_name)
                return {
                    "status": "exists",
                    "collection_name": config.collection_name,
                    "dimension": config.dimension,
                }

            # Create index with config parameters or defaults
            metric = config.metric_type.lower() if config.metric_type else "cosine"
            self.pc.create_index(
                name=config.collection_name,
                dimension=config.dimension,
                metric=metric,
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )

            logging.info(
                "Collection '%s' created successfully with dimension %d", config.collection_name, config.dimension
            )
            return {
                "status": "created",
                "collection_name": config.collection_name,
                "dimension": config.dimension,
                "metric_type": config.metric_type,
            }
        except Exception as e:
            logging.error("Failed to create collection '%s': %s", config.collection_name, str(e))
            raise CollectionError(f"Failed to create collection '{config.collection_name}': {e}") from e

    def create_collection(self, collection_name: str, metadata: dict | None = None) -> None:
        """Create a collection (index) in Pinecone (backward compatibility wrapper).

        Args:
            collection_name: Name of the collection to create
            metadata: Optional metadata for the collection

        Raises:
            CollectionError: If collection creation fails
        """
        try:
            # Create CollectionConfig from legacy parameters
            config = CollectionConfig(
                collection_name=collection_name,
                dimension=self.settings.embedding_dim,
                metric_type="COSINE",
                index_type="HNSW",  # Pinecone default
                description=metadata.get("description") if metadata else None,
            )

            # Use new Pydantic-based implementation
            self._create_collection_impl(config)
        except Exception as e:
            logging.error("Failed to create collection '%s': %s", collection_name, str(e))
            raise CollectionError(f"Failed to create collection '{collection_name}': {e}") from e

    def _add_documents_impl(self, collection_name: str, chunks: list[EmbeddedChunk]) -> list[str]:
        """Implementation-specific document addition with Pydantic models.

        Args:
            collection_name: Target collection
            chunks: List of embedded chunks to add (Pydantic models)

        Returns:
            List of chunk IDs that were added

        Raises:
            DocumentError: If addition fails
        """
        try:
            index = self.pc.Index(collection_name)

            # Prepare vectors for upsert
            vectors = []
            chunk_ids = []

            for chunk in chunks:
                vectors.append(
                    {
                        "id": chunk.chunk_id,
                        "values": chunk.embeddings,  # EmbeddedChunk ensures embeddings are present
                        "metadata": {
                            "text": chunk.text,
                            "document_id": chunk.document_id or "",
                            "source": str(chunk.metadata.source)
                            if chunk.metadata and chunk.metadata.source
                            else "OTHER",
                            "page_number": chunk.metadata.page_number if chunk.metadata else 0,
                            "chunk_number": chunk.metadata.chunk_number if chunk.metadata else 0,
                        },
                    }
                )
                chunk_ids.append(chunk.chunk_id)

            # Upsert vectors
            index.upsert(vectors=vectors)

            logging.info("Successfully added %d chunks to collection '%s'", len(chunks), collection_name)
            return chunk_ids
        except Exception as e:
            logging.error("Failed to add chunks to Pinecone collection '%s': %s", collection_name, str(e))
            raise DocumentError(f"Failed to add chunks to Pinecone collection '{collection_name}': {e}") from e

    def add_documents(self, collection_name: str, documents: list[Document]) -> list[str]:
        """Add documents to the Pinecone collection (backward compatibility wrapper).

        Args:
            collection_name: Name of the collection
            documents: List of documents to add

        Returns:
            List[str]: List of document IDs that were added

        Raises:
            DocumentError: If document addition fails
        """
        try:
            # Convert documents to EmbeddedChunks
            chunks: list[EmbeddedChunk] = []
            for document in documents:
                for chunk in document.chunks:
                    # Only add chunks that have embeddings
                    if chunk.embeddings:
                        embedded_chunk = EmbeddedChunk(
                            chunk_id=chunk.chunk_id,
                            text=chunk.text,
                            embeddings=chunk.embeddings,
                            metadata=chunk.metadata,
                            document_id=chunk.document_id,
                        )
                        chunks.append(embedded_chunk)

            # Use Pydantic-based implementation
            chunk_ids = self._add_documents_impl(collection_name, chunks)

            # Return unique document IDs (for backward compatibility)
            document_ids = list({chunk.document_id for chunk in chunks if chunk.document_id})
            logging.info(
                "Successfully added %d documents (%d chunks) to collection '%s'",
                len(document_ids),
                len(chunk_ids),
                collection_name,
            )
            return document_ids
        except Exception as e:
            logging.error("Failed to add documents to Pinecone collection '%s': %s", collection_name, str(e))
            raise DocumentError(f"Failed to add documents to Pinecone collection '{collection_name}': {e}") from e

    def retrieve_documents(self, query: str, collection_name: str, number_of_results: int = 10) -> list[QueryResult]:
        """Retrieve documents based on a query string.

        Args:
            query: The query string
            collection_name: Name of the collection to search
            number_of_results: Maximum number of results to return

        Returns:
            List[QueryResult]: List of query results

        Raises:
            DocumentError: If retrieval fails
        """
        query_embeddings = get_embeddings_for_vector_store(query, settings=self.settings)
        if not query_embeddings:
            raise DocumentError("Failed to generate embeddings for the query string.")

        query_with_embedding = QueryWithEmbedding(text=query, embeddings=query_embeddings[0])
        return self.query(collection_name, query_with_embedding, number_of_results=number_of_results)

    def _search_impl(self, request: VectorSearchRequest) -> list[QueryResult]:
        """Implementation-specific search with Pydantic model.

        Args:
            request: Vector search request (Pydantic model)

        Returns:
            List of query results

        Raises:
            VectorStoreError: If search fails
        """
        try:
            index = self.pc.Index(request.collection_id)

            # Get query vector (either from request or generate from text)
            if request.query_vector:
                query_embedding = request.query_vector
            elif request.query_text:
                embeddings_list = get_embeddings_for_vector_store(request.query_text, settings=self.settings)
                if not embeddings_list:
                    raise DocumentError("Failed to generate embeddings for query text")
                query_embedding = embeddings_list[0]
            else:
                raise ValueError("Either query_text or query_vector must be provided")

            # Perform query
            results = index.query(vector=query_embedding, top_k=request.top_k, include_metadata=True)

            logging.info("Pinecone search complete for collection '%s'", request.collection_id)
            return self._process_search_results(results, request.collection_id)
        except Exception as e:
            logging.error("Failed to search Pinecone collection '%s': %s", request.collection_id, str(e))
            raise VectorStoreError(f"Failed to search Pinecone collection '{request.collection_id}': {e}") from e

    def query(
        self,
        collection_name: str,
        query: QueryWithEmbedding,
        number_of_results: int = 10,
        metadata_filter: DocumentMetadataFilter | None = None,
    ) -> list[QueryResult]:
        """Query the Pinecone collection (backward compatibility wrapper).

        Args:
            collection_name: Name of the collection to query
            query: Query with embedding
            number_of_results: Maximum number of results to return
            metadata_filter: Optional metadata filter

        Returns:
            List[QueryResult]: List of query results

        Raises:
            DocumentError: If query fails
        """
        try:
            # Create VectorSearchRequest from legacy parameters
            request = VectorSearchRequest(
                query_text=query.text if hasattr(query, "text") else None,
                query_vector=query.embeddings,
                collection_id=collection_name,
                top_k=number_of_results,
                metadata_filter=metadata_filter,
                include_metadata=True,
                include_vectors=False,
            )

            # Use Pydantic-based implementation
            return self._search_impl(request)
        except Exception as e:
            logging.error("Failed to query Pinecone collection '%s': %s", collection_name, str(e))
            raise DocumentError(f"Failed to query Pinecone collection '{collection_name}': {e}") from e

    def delete_collection(self, collection_name: str) -> None:
        """Delete a collection from Pinecone.

        Args:
            collection_name: Name of the collection to delete

        Raises:
            CollectionError: If deletion fails
        """
        try:
            self.pc.delete_index(collection_name)
            logging.info("Deleted collection '%s'", collection_name)
        except Exception as e:
            logging.error("Failed to delete Pinecone collection: %s", str(e))
            raise CollectionError(f"Failed to delete Pinecone collection: {e}") from e

    def delete_documents_with_response(
        self, collection_name: str, document_ids: list[str]
    ) -> VectorDBResponse[dict[str, Any]]:
        """Delete documents and return detailed response (Pydantic-enhanced).

        Args:
            collection_name: Name of the collection
            document_ids: List of document IDs to delete

        Returns:
            VectorDBResponse with deletion metadata
        """
        start_time = time.time()
        try:
            index = self.pc.Index(collection_name)

            # Get all vectors with the specified document_ids
            # Note: Pinecone doesn't support filtering by metadata in delete operations
            # We need to query first to get the vector IDs, then delete them
            total_deleted = 0
            for doc_id in document_ids:
                # Query for vectors with this document_id
                results = index.query(
                    vector=[0.0] * self.settings.embedding_dim,  # Dummy vector
                    top_k=10000,  # Large number to get all vectors
                    include_metadata=True,
                    filter={"document_id": doc_id},
                )

                # Extract vector IDs and delete them
                vector_ids = [match["id"] for match in results["matches"]]
                if vector_ids:
                    index.delete(ids=vector_ids)
                    total_deleted += len(vector_ids)

            elapsed = time.time() - start_time
            logging.info(
                "Deleted %d documents (%d vectors) from collection '%s' in %.2fs",
                len(document_ids),
                total_deleted,
                collection_name,
                elapsed,
            )

            return VectorDBResponse.create_success(
                data={
                    "deleted_count": len(document_ids),
                    "deleted_vectors": total_deleted,
                    "collection_name": collection_name,
                    "document_ids": document_ids,
                },
                metadata={"elapsed_seconds": elapsed},
            )
        except Exception as e:
            elapsed = time.time() - start_time
            logging.error("Failed to delete documents from Pinecone collection '%s': %s", collection_name, str(e))
            return VectorDBResponse.create_error(
                error=f"Failed to delete documents: {e!s}",
                metadata={
                    "collection_name": collection_name,
                    "document_count": len(document_ids),
                    "elapsed_seconds": elapsed,
                },
            )

    def delete_documents(self, collection_name: str, document_ids: list[str]) -> None:
        """Delete documents by their IDs from the Pinecone collection (backward compatibility).

        Args:
            collection_name: Name of the collection
            document_ids: List of document IDs to delete

        Raises:
            DocumentError: If deletion fails
        """
        response = self.delete_documents_with_response(collection_name, document_ids)
        if not response.success:
            raise DocumentError(response.error or "Unknown error during deletion")

    def count_document_chunks(self, collection_name: str, document_id: str) -> int:
        """Count the number of chunks for a specific document.

        Args:
            collection_name: Name of the collection to search in
            document_id: The document ID to count chunks for

        Returns:
            Number of chunks found for the document

        Raises:
            CollectionError: If collection doesn't exist
            DocumentError: If counting fails
        """
        try:
            index = self.pc.Index(collection_name)
            # Query with filter and large top_k to get all matching vectors
            results = index.query(
                vector=[0.0] * self.settings.embedding_dim,  # Dummy vector
                top_k=10000,  # Large number to get all vectors for this document
                include_metadata=True,
                filter={"document_id": document_id},
            )
            chunk_count = len(results.get("matches", []))
            logging.debug("Found %d chunks for document %s in collection %s", chunk_count, document_id, collection_name)
            return chunk_count
        except Exception as e:
            logging.warning(
                "Error counting chunks for document %s in collection %s: %s", document_id, collection_name, str(e)
            )
            raise DocumentError(
                f"Failed to count chunks for document '{document_id}' in collection '{collection_name}': {e}"
            ) from e

    def _process_search_results(self, results: Any, collection_name: str) -> list[QueryResult]:  # noqa: ARG002
        """Process Pinecone search results into QueryResult objects."""
        query_results = []

        for match in results["matches"]:
            metadata = match.get("metadata", {})

            # Create DocumentChunkWithScore
            chunk = DocumentChunkWithScore(
                chunk_id=match["id"],
                text=metadata.get("text", ""),
                embeddings=None,  # Pinecone doesn't return embeddings in search results
                metadata=DocumentChunkMetadata(
                    source=Source(metadata.get("source", "OTHER")),
                    document_id=metadata.get("document_id", ""),
                    page_number=metadata.get("page_number", 0),
                    chunk_number=metadata.get("chunk_number", 0),
                ),
                document_id=metadata.get("document_id", ""),
                score=float(match["score"]),
            )

            query_results.append(QueryResult(chunk=chunk, score=float(match["score"]), embeddings=[]))

        return query_results
