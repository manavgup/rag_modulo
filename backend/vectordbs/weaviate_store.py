"""Weaviate vector store implementation.

This module provides a Weaviate-based implementation of the VectorStore interface,
enabling document storage, retrieval, and search operations using Weaviate.
"""

# pylint: disable=no-member

import logging
import time
from typing import Any

import weaviate

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


class WeaviateDataStore(VectorStore):
    """Weaviate implementation of the VectorStore interface.

    This class provides Weaviate-based vector storage and retrieval capabilities,
    including document management, collection operations, and similarity search.
    """

    def __init__(self, settings: Settings = get_settings()) -> None:
        # Call parent constructor for proper dependency injection
        super().__init__(settings)

        # Configure logging
        logging.basicConfig(level=getattr(self.settings, "log_level", "INFO"))

        # Initialize Weaviate client using v4 API
        auth_credentials = self._build_auth_credentials()
        try:
            logging.debug(
                "Connecting to weaviate instance at %s & %s with credential type %s",
                self.settings.weaviate_host,
                self.settings.weaviate_port,
                type(auth_credentials).__name__,
            )
            self.client = weaviate.connect_to_custom(
                http_host=self.settings.weaviate_host or "localhost",
                http_port=self.settings.weaviate_port or 8080,
                http_secure=False,
                grpc_host=self.settings.weaviate_host or "localhost",
                grpc_port=self.settings.weaviate_grpc_port or 50051,
                grpc_secure=False,
                auth_credentials=auth_credentials,
            )
        except Exception as e:
            logging.error("Failed to connect to Weaviate: %s", str(e))
            raise CollectionError(f"Failed to connect to Weaviate: {e}") from e

    def _build_auth_credentials(self) -> Any:
        """Build authentication credentials for Weaviate."""
        if self.settings.weaviate_username and self.settings.weaviate_password:
            return weaviate.auth.AuthClientPassword(
                self.settings.weaviate_username, self.settings.weaviate_password, self.settings.weaviate_scopes
            )
        return None

    def _create_schema(self, collection_name: str) -> None:
        """Create the schema for Weaviate collection."""
        class_schema = {
            "class": collection_name,
            "description": f"Collection for {collection_name}",
            "vectorizer": "none",  # We'll provide our own vectors
            "properties": [
                {"name": "text", "dataType": ["text"], "description": "The text content of the document chunk"},
                {
                    "name": "document_id",
                    "dataType": ["string"],
                    "description": "The ID of the document this chunk belongs to",
                },
                {"name": "chunk_id", "dataType": ["string"], "description": "The unique ID of this chunk"},
                {"name": "source", "dataType": ["string"], "description": "The source of the document"},
                {"name": "page_number", "dataType": ["int"], "description": "The page number of the chunk"},
                {
                    "name": "chunk_number",
                    "dataType": ["int"],
                    "description": "The number of the chunk within the document",
                },
            ],
        }

        self.client.schema.create_class(class_schema)  # type: ignore[attr-defined]

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

            # Check if class already exists
            if self.client.schema.exists(config.collection_name):  # type: ignore[attr-defined]
                logging.info("Collection '%s' already exists", config.collection_name)
                return {
                    "status": "exists",
                    "collection_name": config.collection_name,
                    "dimension": config.dimension,
                }

            self._create_schema(config.collection_name)
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
        """Create a collection (class) in Weaviate (backward compatibility wrapper).

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
                index_type="HNSW",  # Weaviate default
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
            chunk_ids = []

            for chunk in chunks:
                # Create data object
                data_object = {
                    "text": chunk.text,
                    "document_id": chunk.document_id or "",
                    "chunk_id": chunk.chunk_id,
                    "source": str(chunk.metadata.source) if chunk.metadata and chunk.metadata.source else "OTHER",
                    "page_number": chunk.metadata.page_number if chunk.metadata else 0,
                    "chunk_number": chunk.metadata.chunk_number if chunk.metadata else 0,
                }

                # Add to Weaviate with vector
                self.client.data_object.create(  # type: ignore[attr-defined]
                    data_object=data_object, class_name=collection_name, vector=chunk.embeddings
                )

                chunk_ids.append(chunk.chunk_id)

            logging.info("Successfully added %d chunks to collection '%s'", len(chunks), collection_name)
            return chunk_ids
        except Exception as e:
            logging.error("Failed to add chunks to Weaviate collection '%s': %s", collection_name, str(e))
            raise DocumentError(f"Failed to add chunks to Weaviate collection '{collection_name}': {e}") from e

    def add_documents(self, collection_name: str, documents: list[Document]) -> list[str]:
        """Add documents to the Weaviate collection (backward compatibility wrapper).

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
            logging.error("Failed to add documents to Weaviate collection '%s': %s", collection_name, str(e))
            raise DocumentError(f"Failed to add documents to Weaviate collection '{collection_name}': {e}") from e

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

            # Perform vector search
            results = (
                self.client.query.get(  # type: ignore[attr-defined]
                    class_name=request.collection_id,
                    properties=["text", "document_id", "chunk_id", "source", "page_number", "chunk_number"],
                )
                .with_near_vector({"vector": query_embedding})
                .with_limit(request.top_k)
                .do()
            )

            logging.info("Weaviate search complete for collection '%s'", request.collection_id)
            return self._process_search_results(results, request.collection_id)
        except Exception as e:
            logging.error("Failed to search Weaviate collection '%s': %s", request.collection_id, str(e))
            raise VectorStoreError(f"Failed to search Weaviate collection '{request.collection_id}': {e}") from e

    def query(  # pylint: disable=redefined-builtin
        self,
        collection_name: str,
        query: QueryWithEmbedding,
        number_of_results: int = 10,
        filter: DocumentMetadataFilter | None = None,
    ) -> list[QueryResult]:
        """Query the Weaviate collection (backward compatibility wrapper).

        Args:
            collection_name: Name of the collection to query
            query: Query with embedding
            number_of_results: Maximum number of results to return
            filter: Optional metadata filter

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
                metadata_filter=filter,
                include_metadata=True,
                include_vectors=False,
            )

            # Use Pydantic-based implementation
            return self._search_impl(request)
        except Exception as e:
            logging.error("Failed to query Weaviate collection '%s': %s", collection_name, str(e))
            raise DocumentError(f"Failed to query Weaviate collection '{collection_name}': {e}") from e

    def delete_collection(self, collection_name: str) -> None:
        """Delete a collection from Weaviate.

        Args:
            collection_name: Name of the collection to delete

        Raises:
            CollectionError: If deletion fails
        """
        try:
            if self.client.schema.exists(collection_name):  # type: ignore[attr-defined]
                self.client.schema.delete_class(collection_name)  # type: ignore[attr-defined]
                logging.info("Deleted collection '%s'", collection_name)
        except Exception as e:
            logging.error("Failed to delete Weaviate collection: %s", str(e))
            raise CollectionError(f"Failed to delete Weaviate collection: {e}") from e

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
            deleted_count = 0

            # Query for objects with the specified document_ids
            for doc_id in document_ids:
                results = (
                    self.client.query.get(  # type: ignore[attr-defined]
                        class_name=collection_name, properties=["document_id"]
                    )
                    .with_where({"path": ["document_id"], "operator": "Equal", "valueString": doc_id})
                    .do()
                )

                # Delete each object
                for obj in results["data"]["Get"][collection_name]:
                    self.client.data_object.delete(  # type: ignore[attr-defined]
                        uuid=obj["_additional"]["id"], class_name=collection_name
                    )
                    deleted_count += 1

            elapsed = time.time() - start_time
            logging.info("Deleted %d documents from collection '%s' in %.2fs", deleted_count, collection_name, elapsed)

            return VectorDBResponse.create_success(
                data={
                    "deleted_count": deleted_count,
                    "collection_name": collection_name,
                    "document_ids": document_ids,
                },
                metadata={"elapsed_seconds": elapsed},
            )
        except Exception as e:
            elapsed = time.time() - start_time
            logging.error("Failed to delete documents from Weaviate collection '%s': %s", collection_name, str(e))
            return VectorDBResponse.create_error(
                error=f"Failed to delete documents: {e!s}",
                metadata={
                    "collection_name": collection_name,
                    "document_count": len(document_ids),
                    "elapsed_seconds": elapsed,
                },
            )

    def delete_documents(self, collection_name: str, document_ids: list[str]) -> None:
        """Delete documents by their IDs from the Weaviate collection (backward compatibility).

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
            # Query for all chunks with the specified document_id
            results = (
                self.client.query.aggregate(collection_name)  # type: ignore[attr-defined]
                .with_where({"path": ["document_id"], "operator": "Equal", "valueString": document_id})
                .with_meta_count()
                .do()
            )
            # Extract count from aggregation results
            chunk_count = results["data"]["Aggregate"][collection_name][0]["meta"]["count"]
            logging.debug("Found %d chunks for document %s in collection %s", chunk_count, document_id, collection_name)
            return chunk_count
        except (KeyError, IndexError, TypeError) as e:
            logging.warning(
                "Error parsing count results for document %s in collection %s: %s", document_id, collection_name, str(e)
            )
            return 0
        except Exception as e:
            logging.warning(
                "Error counting chunks for document %s in collection %s: %s", document_id, collection_name, str(e)
            )
            raise DocumentError(
                f"Failed to count chunks for document '{document_id}' in collection '{collection_name}': {e}"
            ) from e

    def _process_search_results(self, results: Any, collection_name: str) -> list[QueryResult]:
        """Process Weaviate search results into QueryResult objects."""
        query_results = []

        for obj in results["data"]["Get"][collection_name]:
            # Create DocumentChunkWithScore
            chunk = DocumentChunkWithScore(
                chunk_id=obj["chunk_id"],
                text=obj["text"],
                embeddings=None,  # Weaviate doesn't return embeddings in search results
                metadata=DocumentChunkMetadata(
                    source=Source(obj["source"]),
                    document_id=obj["document_id"],
                    page_number=obj["page_number"],
                    chunk_number=obj["chunk_number"],
                ),
                document_id=obj["document_id"],
                score=float(obj["_additional"]["distance"]),  # Convert distance to score
            )

            query_results.append(QueryResult(chunk=chunk, score=float(obj["_additional"]["distance"]), embeddings=[]))

        return query_results
