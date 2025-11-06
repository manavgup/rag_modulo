"""Milvus vector store implementation.

This module provides a Milvus-based implementation of the VectorStore interface,
enabling document storage, retrieval, and search operations using Milvus.
"""

import json
import logging
import time
from typing import Any

from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, MilvusException, connections, utility

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

# Remove module-level constants - use dependency injection instead


def _create_schema(settings: Settings) -> list[FieldSchema]:
    """Create the schema for Milvus collection with injected settings."""
    return [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="document_id", dtype=DataType.VARCHAR, max_length=65535),
        FieldSchema(name=settings.embedding_field, dtype=DataType.FLOAT_VECTOR, dim=settings.embedding_dim),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
        FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=100),
        # Document metadata fields
        FieldSchema(name="document_name", dtype=DataType.VARCHAR, max_length=65535),
        # Chunk metadata fields
        FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=20),
        FieldSchema(name="page_number", dtype=DataType.INT64),
        FieldSchema(name="chunk_number", dtype=DataType.INT64),
    ]


class MilvusStore(VectorStore):
    """Milvus implementation of the VectorStore interface.

    This class provides Milvus-based vector storage and retrieval capabilities,
    including document management, collection operations, and similarity search.
    """

    def __init__(self, settings: Settings = get_settings()) -> None:
        # Call parent constructor for proper dependency injection
        super().__init__(settings)

        # Configure logging
        logging.basicConfig(level=getattr(self.settings, "log_level", "INFO"))

        # Initialize connection
        self._connect()

        # Initialize index and search parameters
        self.index_params = {"metric_type": "COSINE", "index_type": "IVF_FLAT", "params": {"nlist": 1024}}
        self.search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}

    def _connect(self, attempts: int = 3) -> None:
        """Connect to Milvus with retry logic."""
        host = self.settings.milvus_host or "localhost"
        port = self.settings.milvus_port or 19530

        # Disconnect any existing connection first to avoid using cached connection with old host
        try:
            connections.disconnect("default")
            logging.info("Disconnected existing Milvus connection")
        except Exception:
            pass  # No existing connection, continue

        for attempt in range(attempts):
            try:
                connections.connect("default", host=host, port=port)
                logging.info("Connected to Milvus at %s:%s", host, port)
                return
            except MilvusException as e:
                logging.error("Failed to connect to Milvus at %s:%s: %s", host, port, str(e))
                if attempt < attempts - 1:
                    logging.info("Retrying connection to Milvus... (Attempt %d/%d)", attempt + 2, attempts)
                    time.sleep(10)
                raise VectorStoreError(f"Failed to connect to Milvus after {attempts} attempts") from e

    def _get_collection(self, collection_name: str) -> Collection:
        """Retrieve a collection from Milvus.

        Args:
            collection_name: Name of the collection

        Returns:
            Collection: The Milvus collection

        Raises:
            CollectionError: If collection doesn't exist
        """
        if utility.has_collection(collection_name):
            return Collection(name=collection_name)
        raise CollectionError(f"Collection '{collection_name}' does not exist")

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

            # Check if collection already exists
            if config.collection_name in utility.list_collections():
                logging.info("Collection '%s' already exists", config.collection_name)
                return {
                    "status": "exists",
                    "collection_name": config.collection_name,
                    "dimension": config.dimension,
                }

            # Create schema
            schema = CollectionSchema(
                fields=_create_schema(self.settings),
                description=config.description or f"Collection for {config.collection_name}",
            )
            collection = Collection(name=config.collection_name, schema=schema)

            # Create index with config parameters or defaults
            index_params = {
                "metric_type": config.metric_type or "COSINE",
                "index_type": config.index_type or "IVF_FLAT",
                "params": config.index_params or {"nlist": 1024},
            }
            collection.create_index(field_name=self.settings.embedding_field, index_params=index_params)

            # Load collection
            collection.load()

            logging.info(
                "Collection '%s' created successfully with dimension %d", config.collection_name, config.dimension
            )
            return {
                "status": "created",
                "collection_name": config.collection_name,
                "dimension": config.dimension,
                "metric_type": config.metric_type,
                "index_type": config.index_type,
            }
        except Exception as e:
            logging.error("Failed to create collection '%s': %s", config.collection_name, str(e))
            raise CollectionError(f"Failed to create collection '{config.collection_name}': {e}") from e

    def create_collection(self, collection_name: str, metadata: dict | None = None) -> Collection:
        """Create a new Milvus collection (backward compatibility wrapper).

        Args:
            collection_name: Name of the collection to create
            metadata: Optional metadata for the collection

        Returns:
            Collection: The created collection

        Raises:
            CollectionError: If collection creation fails
        """
        try:
            # Create CollectionConfig from legacy parameters
            config = CollectionConfig(
                collection_name=collection_name,
                dimension=self.settings.embedding_dim,
                metric_type="COSINE",
                index_type="IVF_FLAT",
                index_params={"nlist": 1024},
                description=metadata.get("description") if metadata else None,
            )

            # Use new Pydantic-based implementation
            self._create_collection_impl(config)
            return Collection(name=collection_name)
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
            collection = self._get_collection(collection_name)

            # Prepare data for insertion using Pydantic models
            document_ids = []
            texts = []
            embeddings = []
            chunk_ids = []
            sources = []
            page_numbers = []
            chunk_numbers = []
            document_names = []

            for chunk in chunks:
                document_ids.append(chunk.document_id or "")
                texts.append(chunk.text)
                embeddings.append(chunk.embeddings)  # EmbeddedChunk ensures embeddings are present
                chunk_ids.append(chunk.chunk_id)
                sources.append(str(chunk.metadata.source) if chunk.metadata and chunk.metadata.source else "OTHER")
                page_numbers.append(
                    chunk.metadata.page_number if chunk.metadata and chunk.metadata.page_number is not None else 0
                )
                chunk_numbers.append(
                    chunk.metadata.chunk_number if chunk.metadata and chunk.metadata.chunk_number is not None else 0
                )
                # Extract document name from metadata if available
                document_names.append(getattr(chunk.metadata, "title", "") if chunk.metadata else "")

            # Insert data
            collection.insert(
                [
                    document_ids,
                    embeddings,
                    texts,
                    chunk_ids,
                    document_names,
                    sources,
                    page_numbers,
                    chunk_numbers,
                ]
            )

            # Flush to ensure data is written
            collection.flush()

            logging.info("Successfully added %d chunks to collection '%s'", len(chunks), collection_name)
            return chunk_ids
        except Exception as e:
            logging.error("Failed to add chunks to Milvus collection '%s': %s", collection_name, str(e))
            raise DocumentError(f"Failed to add chunks to Milvus collection '{collection_name}': {e}") from e

    def add_documents(self, collection_name: str, documents: list[Document]) -> list[str]:
        """Add documents to the Milvus collection (backward compatibility wrapper).

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
            logging.error("Failed to add documents to Milvus collection '%s': %s", collection_name, str(e))
            raise DocumentError(f"Failed to add documents to Milvus collection '{collection_name}': {e}") from e

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
        # DEBUG: Log before embedding generation
        logger.debug(
            "MilvusDB.retrieve: query='%s...', collection=%s, n=%d",
            query[:50] if len(query) > 50 else query,
            collection_name,
            number_of_results,
        )

        query_embeddings = get_embeddings_for_vector_store(query, settings=self.settings)
        if not query_embeddings:
            raise DocumentError("Failed to generate embeddings for the query string.")

        # DEBUG: Log embedding details
        embedding = query_embeddings[0]
        logger.info("  Generated embedding dimension: %d", len(embedding))
        logger.info("  Embedding sample (first 5 values): %s", embedding[:5])

        query_with_embedding = QueryWithEmbedding(text=query, embeddings=query_embeddings[0])
        results = self.query(collection_name, query_with_embedding, number_of_results=number_of_results)

        # DEBUG: Log detailed results for debugging
        logger.info("  Milvus returned %d results", len(results))
        if results:
            logger.info("  Detailed results from retrieve_documents():")
            for i, result in enumerate(results[:5], 1):  # Log first 5 results
                page_num = getattr(result.chunk.metadata, "page_number", -1) if result.chunk.metadata else -1
                text_preview = result.chunk.text[:80] if result.chunk and result.chunk.text else "N/A"
                logger.info("    Result %d: score=%.4f, page=%d, text='%s...'", i, result.score, page_num, text_preview)
            if len(results) > 5:
                logger.info("    ... and %d more results", len(results) - 5)

        return results

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
            collection = self._get_collection(request.collection_id)

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

            # Perform search
            results = collection.search(
                data=[query_embedding],
                anns_field=self.settings.embedding_field,
                param=self.search_params,
                limit=request.top_k,
                output_fields=[
                    "document_id",
                    "text",
                    "chunk_id",
                    "source",
                    "page_number",
                    "chunk_number",
                    "document_name",
                ],
            )

            # Log summary
            if results and hasattr(results, "__len__"):
                logger.info(
                    "Milvus search complete: %d results returned for collection '%s'",
                    len(results),
                    request.collection_id,
                )
            else:
                logger.debug("Milvus search returned results (non-list type)")

            return self._process_search_results(results, request.collection_id)
        except Exception as e:
            logging.error("Failed to search Milvus collection '%s': %s", request.collection_id, str(e))
            raise VectorStoreError(f"Failed to search Milvus collection '{request.collection_id}': {e}") from e

    def query(
        self,
        collection_name: str,
        query: QueryWithEmbedding,
        number_of_results: int = 10,
        metadata_filter: DocumentMetadataFilter | None = None,
    ) -> list[QueryResult]:
        """Query the Milvus collection (backward compatibility wrapper).

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
            logging.error("Failed to query Milvus collection '%s': %s", collection_name, str(e))
            raise DocumentError(f"Failed to query Milvus collection '{collection_name}': {e}") from e

    def delete_collection(self, collection_name: str) -> None:
        """Delete a collection from Milvus.

        Args:
            collection_name: Name of the collection to delete

        Raises:
            CollectionError: If deletion fails
        """
        try:
            if utility.has_collection(collection_name):
                utility.drop_collection(collection_name)
                logging.info("Deleted collection '%s'", collection_name)
        except Exception as e:
            logging.error("Failed to delete Milvus collection: %s", str(e))
            raise CollectionError(f"Failed to delete Milvus collection: {e}") from e

    def list_collections(self) -> list[str]:
        """List all collections in Milvus.

        Returns:
            List of collection names

        Raises:
            CollectionError: If listing fails
        """
        try:
            collections = utility.list_collections()
            logging.info("Listed %d collections from Milvus", len(collections))
            return collections
        except Exception as e:
            logging.error("Failed to list Milvus collections: %s", str(e))
            raise CollectionError(f"Failed to list Milvus collections: {e}") from e

    def delete_documents_with_response(
        self, collection_name: str, document_ids: list[str]
    ) -> VectorDBResponse[dict[str, Any]]:
        """Delete documents and return detailed response (Pydantic-enhanced).

        Args:
            collection_name: Name of the collection
            document_ids: List of document IDs to delete

        Returns:
            VectorDBResponse with deletion metadata

        Raises:
            DocumentError: If deletion fails
        """
        start_time = time.time()
        try:
            collection = self._get_collection(collection_name)

            # Build filter expression
            filter_expr = f"document_id in {json.dumps(document_ids)}"

            # Delete documents
            collection.delete(filter_expr)

            # Flush to ensure deletion is applied
            collection.flush()

            elapsed = time.time() - start_time
            logging.info(
                "Deleted %d documents from collection '%s' in %.2fs", len(document_ids), collection_name, elapsed
            )

            return VectorDBResponse.create_success(
                data={
                    "deleted_count": len(document_ids),
                    "collection_name": collection_name,
                    "document_ids": document_ids,
                },
                metadata={"elapsed_seconds": elapsed},
            )
        except Exception as e:
            elapsed = time.time() - start_time
            logging.error("Failed to delete documents from Milvus collection '%s': %s", collection_name, str(e))
            return VectorDBResponse.create_error(
                error=f"Failed to delete documents: {e!s}",
                metadata={
                    "collection_name": collection_name,
                    "document_count": len(document_ids),
                    "elapsed_seconds": elapsed,
                },
            )

    def delete_documents(self, collection_name: str, document_ids: list[str]) -> None:
        """Delete documents by their IDs from the Milvus collection (backward compatibility).

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
            collection = self._get_collection(collection_name)

            # Escape document_id to prevent injection attacks
            # Use JSON encoding for proper string escaping
            escaped_doc_id = json.dumps(document_id)

            # Query with expression filter for document_id
            results = collection.query(
                expr=f"document_id == {escaped_doc_id}",
                output_fields=["id"],  # Only need count, minimal fields
                limit=10000,  # Max chunks per document
            )

            chunk_count = len(results) if results else 0
            logging.debug("Found %d chunks for document %s in collection %s", chunk_count, document_id, collection_name)
            return chunk_count

        except CollectionError:
            # Re-raise collection errors
            raise
        except Exception as e:
            logging.warning(
                "Error counting chunks for document %s in collection %s: %s", document_id, collection_name, str(e)
            )
            raise DocumentError(
                f"Failed to count chunks for document '{document_id}' in collection '{collection_name}': {e}"
            ) from e

    def _process_search_results(self, results: Any, collection_name: str) -> list[QueryResult]:  # noqa: ARG002
        """Process Milvus search results into QueryResult objects."""
        query_results = []

        # DEBUG: Log raw Milvus hits before processing
        if results and len(results) > 0:
            logger.debug("Processing %d raw Milvus hits from results[0]", len(results[0]))

        for idx, hit in enumerate(results[0], 1):  # results is a list of hits for each query
            # Extract data from hit using proper Milvus Hit API
            entity = hit.entity
            document_id = getattr(entity, "document_id", "")
            text = getattr(entity, "text", "")
            chunk_id = getattr(entity, "chunk_id", "")
            source = getattr(entity, "source", "OTHER")
            page_number = getattr(entity, "page_number", 0)
            chunk_number = getattr(entity, "chunk_number", 0)

            # Create DocumentChunkWithScore
            chunk = DocumentChunkWithScore(
                chunk_id=chunk_id,
                text=text,
                embeddings=None,  # Milvus doesn't return embeddings in search results
                metadata=DocumentChunkMetadata(
                    source=Source(source.lower().replace("source.", "") if source else "other"),
                    document_id=document_id,
                    page_number=page_number,
                    chunk_number=chunk_number,
                ),
                document_id=document_id,
                score=float(hit.score),
            )

            query_results.append(QueryResult(chunk=chunk, score=float(hit.score), embeddings=[]))

            # DEBUG: Log each processed result (first 3 only)
            if idx <= 3:
                text_preview = text[:80] if text else "N/A"
                logger.debug(
                    "  Processed hit %d: score=%.4f, page=%d, chunk=%s, text='%s...'",
                    idx,
                    float(hit.score),
                    page_number,
                    chunk_id,
                    text_preview,
                )

        logger.debug("Total QueryResult objects created: %d", len(query_results))
        return query_results
