"""ChromaDB vector store implementation.

This module provides a ChromaDB-based implementation of the VectorStore interface,
enabling document storage, retrieval, and search operations using ChromaDB.
"""

import logging
from collections.abc import Mapping
from typing import Any

import numpy as np
from chromadb import ClientAPI, chromadb

from core.config import Settings, get_settings
from vectordbs.utils.watsonx import get_embeddings

from .data_types import (
    Document,
    DocumentChunk,
    DocumentChunkMetadata,
    DocumentChunkWithScore,
    DocumentMetadataFilter,
    QueryResult,
    QueryWithEmbedding,
    Source,
)
from .error_types import CollectionError, DocumentError
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

    def create_collection(self, collection_name: str, metadata: dict | None = None) -> None:
        """Create a collection in ChromaDB."""
        try:
            self._client.create_collection(name=collection_name, metadata=metadata)
            logging.info("Collection '%s' created successfully", collection_name)
        except Exception as e:
            logging.error("Failed to create collection '%s': %s", collection_name, str(e))
            raise CollectionError(f"Failed to create collection '{collection_name}': {e}") from e

    def _create_collection_if_not_exists(self, collection_name: str) -> None:
        """Create a collection if it doesn't exist."""
        try:
            self._client.get_collection(collection_name)
        except (ValueError, KeyError, AttributeError):
            self.create_collection(collection_name)

    def add_documents(self, collection_name: str, documents: list[Document]) -> list[str]:
        """Adds documents to the vector store."""
        collection = self._client.get_collection(collection_name)
        self._initialize_client()
        self._create_collection_if_not_exists(collection_name)

        docs, embeddings, metadatas, ids = [], [], [], []

        for document in documents:
            for chunk in document.chunks:
                docs.append(chunk.text)
                embeddings.append(chunk.embeddings)
                metadata: MetadataType = {
                    "source": str(chunk.metadata.source) if chunk.metadata and chunk.metadata.source else "OTHER",
                    "document_id": chunk.document_id or "",
                }
                metadatas.append(metadata)
                ids.append(chunk.chunk_id)

        try:
            # Convert embeddings to the format expected by ChromaDB
            embeddings_array = np.array(embeddings, dtype=np.float32)
            collection.upsert(ids=ids, embeddings=embeddings_array, metadatas=metadatas, documents=docs)  # type: ignore[arg-type]
            logging.info("Successfully added documents to collection '%s'", collection_name)
        except Exception as e:
            logging.error("Failed to add documents to ChromaDB collection '%s': %s", collection_name, str(e))
            raise DocumentError(f"Failed to add documents to ChromaDB collection '{collection_name}': {e}") from e

        return [doc.document_id for doc in documents]

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
        query_embeddings = get_embeddings(query, settings=self.settings)
        if not query_embeddings:
            raise DocumentError("Failed to generate embeddings for the query string.")
        # get_embeddings returns list[list[float]], but we need list[float] for single query
        query_with_embedding = QueryWithEmbedding(text=query, embeddings=query_embeddings[0])
        return self.query(collection_name, query_with_embedding, number_of_results=number_of_results)

    def query(
        self,
        collection_name: str,
        query: QueryWithEmbedding,
        number_of_results: int = 10,
        metadata_filter: DocumentMetadataFilter | None = None,  # noqa: ARG002
    ) -> list[QueryResult]:
        """
        Queries the vector store with filtering and query mode options.

        Args:
            collection_name (str): The name of the collection to query.
            query (QueryWithEmbedding): The query with embedding to search for.
            number_of_results (int): The maximum number of results to return.
            metadata_filter (Optional[DocumentMetadataFilter]): Optional filter to apply to the query.

        Returns:
            List[QueryResult]: The list of query results.
        """
        collection = self._client.get_collection(collection_name)

        try:
            # ChromaDB expects embeddings as list[float], not list[list[float]]
            query_embeddings = query.embeddings[0]
            response = collection.query(
                query_embeddings=query_embeddings,  # type: ignore[arg-type]
                n_results=number_of_results,  # ChromaDB API uses n_results, but we maintain our consistent interface
            )
            logging.info("Query response: %s", response)
            return self._process_search_results(response, collection_name)
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

    def delete_documents(self, collection_name: str, document_ids: list[str]) -> None:
        """Deletes documents by their IDs from the vector store."""
        collection = self._client.get_collection(collection_name)

        try:
            collection.delete(ids=document_ids)
            logging.info("Deleted %d documents from collection '%s'", len(document_ids), collection_name)
            return
        except Exception as e:
            logging.error("Failed to delete documents from ChromaDB collection '%s': %s", collection_name, str(e))
            raise DocumentError(f"Failed to delete documents from ChromaDB collection '{collection_name}': {e}") from e

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
