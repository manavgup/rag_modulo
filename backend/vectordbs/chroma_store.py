"""ChromaDB vector store implementation.

This module provides a ChromaDB-based implementation of the VectorStore interface,
enabling document storage, retrieval, and search operations using ChromaDB.
"""

import logging
import time
from collections.abc import Mapping
from typing import Any

import numpy as np
from chromadb import ClientAPI, chromadb

from core.config import Settings, get_settings

from .data_types import (
    CollectionConfig,
    Document,
    DocumentChunk,
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

# Remove module-level constants - use dependency injection instead

MetadataType = Mapping[str, str | int | float | bool]


class ChromaDBStore(VectorStore):
    """ChromaDB implementation of the VectorStore interface.

    This class provides ChromaDB-based vector storage and retrieval capabilities,
    including document management, collection operations, and similarity search.
    """

    def __init__(self, client: ClientAPI | None = None, settings: Settings = get_settings()) -> None:
        # Call parent constructor for proper dependency injection
        super().__init__(settings)
        self._client: ClientAPI = client or self._initialize_client()

        # Configure logging
        logging.basicConfig(level=getattr(self.settings, "log_level", "INFO"))

    def _initialize_client(self) -> ClientAPI:
        """Initialize the ChromaDB client."""
        try:
            if self.settings.chromadb_host is None or self.settings.chromadb_port is None:
                raise ValueError("ChromaDB host and port must be configured")
            # Assert that values are not None after the check
            assert self.settings.chromadb_host is not None
            assert self.settings.chromadb_port is not None
            client = chromadb.HttpClient(host=self.settings.chromadb_host, port=self.settings.chromadb_port)
            logging.info("Connected to ChromaDB")
            return client
        except Exception as e:
            logging.error("Failed to connect to ChromaDB: %s", str(e))
            raise CollectionError(f"Failed to connect to ChromaDB: {e}") from e

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

            # ChromaDB metadata format
            chroma_metadata: dict[str, Any] = {
                "dimension": config.dimension,
                "metric": config.metric_type.lower(),
            }
            if config.description:
                chroma_metadata["description"] = config.description

            self._client.create_collection(name=config.collection_name, metadata=chroma_metadata)
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
        """Create a collection in ChromaDB (backward compatibility wrapper).

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
                index_type="FLAT",  # ChromaDB default
                description=metadata.get("description") if metadata else None,
            )

            # Use new Pydantic-based implementation
            self._create_collection_impl(config)
        except Exception as e:
            logging.error("Failed to create collection '%s': %s", collection_name, str(e))
            raise CollectionError(f"Failed to create collection '{collection_name}': {e}") from e

    def _create_collection_if_not_exists(self, collection_name: str) -> None:
        """Create a collection if it doesn't exist."""
        try:
            self._client.get_collection(collection_name)
        except (ValueError, KeyError, AttributeError):
            self.create_collection(collection_name)

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
            collection = self._client.get_collection(collection_name)

            docs, embeddings, metadatas, ids = [], [], [], []

            for chunk in chunks:
                docs.append(chunk.text)
                embeddings.append(chunk.embeddings)  # EmbeddedChunk ensures embeddings are present
                metadata: MetadataType = {
                    "source": str(chunk.metadata.source) if chunk.metadata and chunk.metadata.source else "OTHER",
                    "document_id": chunk.document_id or "",
                }
                metadatas.append(metadata)
                ids.append(chunk.chunk_id)

            # Convert embeddings to the format expected by ChromaDB
            embeddings_array = np.array(embeddings, dtype=np.float32)
            collection.upsert(ids=ids, embeddings=embeddings_array, metadatas=metadatas, documents=docs)  # type: ignore[arg-type]
            logging.info("Successfully added %d chunks to collection '%s'", len(chunks), collection_name)

            return ids
        except Exception as e:
            logging.error("Failed to add chunks to ChromaDB collection '%s': %s", collection_name, str(e))
            raise DocumentError(f"Failed to add chunks to ChromaDB collection '{collection_name}': {e}") from e

    def add_documents(self, collection_name: str, documents: list[Document]) -> list[str]:
        """Adds documents to the vector store (backward compatibility wrapper).

        Args:
            collection_name: Name of the collection
            documents: List of documents to add

        Returns:
            List[str]: List of document IDs that were added

        Raises:
            DocumentError: If document addition fails
        """
        self._initialize_client()
        self._create_collection_if_not_exists(collection_name)

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
            self._add_documents_impl(collection_name, chunks)

            # Return unique document IDs (for backward compatibility)
            return [doc.document_id for doc in documents]
        except Exception as e:
            logging.error("Failed to add documents to ChromaDB collection '%s': %s", collection_name, str(e))
            raise DocumentError(f"Failed to add documents to ChromaDB collection '{collection_name}': {e}") from e

    def retrieve_documents(self, query: str, collection_name: str, number_of_results: int = 10) -> list[QueryResult]:
        """
        Retrieves documents based on a query string.

        Args:
            query (str): The query string.
            collection_name (str): The name of the collection to retrieve from.
            number_of_results (int): The maximum number of results to return.

        Returns:
            List[QueryResult]: The list of query results.
        """
        query_embeddings = get_embeddings_for_vector_store(query, settings=self.settings)
        if not query_embeddings:
            raise DocumentError("Failed to generate embeddings for the query string.")
        # get_embeddings returns list[list[float]], but we need list[float] for single query
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
            collection = self._client.get_collection(request.collection_id)

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

            # ChromaDB expects embeddings as list[float]
            response = collection.query(
                query_embeddings=query_embedding,  # type: ignore[arg-type]
                n_results=request.top_k,
            )
            logging.info("ChromaDB search complete for collection '%s'", request.collection_id)
            return self._process_search_results(response, request.collection_id)
        except Exception as e:
            logging.error("Failed to search ChromaDB collection '%s': %s", request.collection_id, str(e))
            raise VectorStoreError(f"Failed to search ChromaDB collection '{request.collection_id}': {e}") from e

    def query(
        self,
        collection_name: str,
        query: QueryWithEmbedding,
        number_of_results: int = 10,
        metadata_filter: DocumentMetadataFilter | None = None,
    ) -> list[QueryResult]:
        """Queries the vector store (backward compatibility wrapper).

        Args:
            collection_name (str): The name of the collection to query.
            query (QueryWithEmbedding): The query with embedding to search for.
            number_of_results (int): The maximum number of results to return.
            metadata_filter (Optional[DocumentMetadataFilter]): Optional filter to apply to the query.

        Returns:
            List[QueryResult]: The list of query results.
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
            logging.error("Failed to query ChromaDB collection '%s': %s", collection_name, str(e))
            raise DocumentError(f"Failed to query ChromaDB collection '{collection_name}': {e}") from e

    def delete_collection(self, collection_name: str) -> None:
        """Deletes a collection from the vector store."""

        try:
            self._client.delete_collection(collection_name)
            logging.info("Deleted collection '%s'", collection_name)
        except Exception as e:
            logging.error("Failed to delete ChromaDB collection: %s", str(e))
            raise CollectionError(f"Failed to delete ChromaDB collection: {e}") from e

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
            collection = self._client.get_collection(collection_name)
            collection.delete(ids=document_ids)

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
            logging.error("Failed to delete documents from ChromaDB collection '%s': %s", collection_name, str(e))
            return VectorDBResponse.create_error(
                error=f"Failed to delete documents: {e!s}",
                metadata={
                    "collection_name": collection_name,
                    "document_count": len(document_ids),
                    "elapsed_seconds": elapsed,
                },
            )

    def delete_documents(self, collection_name: str, document_ids: list[str]) -> None:
        """Deletes documents by their IDs from the vector store (backward compatibility).

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
            collection = self._client.get_collection(collection_name)
            # ChromaDB uses where filter to query by metadata
            results = collection.get(where={"document_id": document_id})
            chunk_count = len(results.get("ids", []))
            logging.debug("Found %d chunks for document %s in collection %s", chunk_count, document_id, collection_name)
            return chunk_count
        except (ValueError, KeyError, AttributeError) as e:
            logging.warning("Collection '%s' not found or error accessing: %s", collection_name, str(e))
            raise CollectionError(f"Collection '{collection_name}' not found: {e}") from e
        except Exception as e:
            logging.warning(
                "Error counting chunks for document %s in collection %s: %s", document_id, collection_name, str(e)
            )
            raise DocumentError(
                f"Failed to count chunks for document '{document_id}' in collection '{collection_name}': {e}"
            ) from e

    def _convert_to_chunk(
        self, chunk_id: str, text: str, embeddings: list[float] | None, metadata: dict
    ) -> DocumentChunk:
        """Convert ChromaDB response data to DocumentChunk."""
        return DocumentChunk(
            chunk_id=chunk_id,
            text=text,
            embeddings=embeddings,
            metadata=DocumentChunkMetadata(
                source=Source(metadata["source"]) if metadata["source"] else Source.OTHER,
                document_id=metadata["document_id"],
            ),
            document_id=metadata["document_id"],
        )

    def _process_search_results(self, response: Any, collection_name: str) -> list[QueryResult]:  # noqa: ARG002
        """Process ChromaDB search results into QueryResult objects."""
        results = []
        ids = response.get("ids", [[]])[0]
        distances = response.get("distances", [[]])[0]
        metadatas = response.get("metadatas", [[]])[0]
        documents = response.get("documents", [[]])[0]

        for i, chunk_id in enumerate(ids):
            base_chunk = self._convert_to_chunk(
                chunk_id=chunk_id,
                text=documents[i],
                embeddings=None,  # Assuming embeddings are not returned in the response, otherwise add appropriate key
                metadata=metadatas[i],
            )
            chunk = DocumentChunkWithScore(
                chunk_id=base_chunk.chunk_id,
                text=base_chunk.text,
                embeddings=base_chunk.embeddings,
                metadata=base_chunk.metadata,
                document_id=base_chunk.document_id,
                score=1.0 - distances[i],
            )
            results.append(QueryResult(chunk=chunk, score=1.0 - distances[i], embeddings=[]))
        return results
