import logging
from collections.abc import Mapping
from typing import Any

from chromadb import ClientAPI, chromadb

from core.config import settings
from vectordbs.utils.watsonx import get_embeddings

from .data_types import (
    Document,
    DocumentChunk,
    DocumentChunkMetadata,
    DocumentMetadataFilter,
    QueryResult,
    QueryWithEmbedding,
    Source,
)
from .error_types import CollectionError, DocumentError
from .vector_store import VectorStore

CHROMADB_HOST = settings.chromadb_host
CHROMADB_PORT = settings.chromadb_port
EMBEDDING_MODEL = settings.embedding_model
EMBEDDING_DIM = settings.embedding_dim

logging.basicConfig(level=settings.log_level)

MetadataType = Mapping[str, str | int | float | bool]


class ChromaDBStore(VectorStore):
    def __init__(self, client: ClientAPI | None = None) -> None:
        self._client: ClientAPI = client or self._initialize_client()

    def _initialize_client(self) -> ClientAPI:
        """Initialize the ChromaDB client."""
        try:
            if CHROMADB_HOST is None or CHROMADB_PORT is None:
                raise ValueError("ChromaDB host and port must be configured")
            # Assert that values are not None after the check
            assert CHROMADB_HOST is not None
            assert CHROMADB_PORT is not None
            client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)
            logging.info("Connected to ChromaDB")
            return client
        except Exception as e:
            logging.error(f"Failed to connect to ChromaDB: {e}")
            raise CollectionError(f"Failed to connect to ChromaDB: {e}") from e

    def create_collection(self, collection_name: str, metadata: dict | None = None) -> None:
        """Create a collection in ChromaDB."""
        try:
            self._client.create_collection(name=collection_name, metadata=metadata)
            logging.info(f"Collection '{collection_name}' created successfully")
        except Exception as e:
            logging.error(f"Failed to create collection '{collection_name}': {e}")
            raise CollectionError(f"Failed to create collection '{collection_name}': {e}") from e

    def _create_collection_if_not_exists(self, collection_name: str) -> None:
        """Create a collection if it doesn't exist."""
        try:
            self._client.get_collection(collection_name)
        except Exception:
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
            import numpy as np

            embeddings_array = np.array(embeddings, dtype=np.float32)
            collection.upsert(ids=ids, embeddings=embeddings_array, metadatas=metadatas, documents=docs)  # type: ignore[arg-type]
            logging.info(f"Successfully added documents to collection '{collection_name}'")
        except Exception as e:
            logging.error(f"Failed to add documents to ChromaDB collection '{collection_name}': {e}")
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
        query_embeddings = get_embeddings(query)
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
        filter: DocumentMetadataFilter | None = None,  # noqa: ARG002
    ) -> list[QueryResult]:
        """
        Queries the vector store with filtering and query mode options.

        Args:
            collection_name (str): The name of the collection to query.
            query (QueryWithEmbedding): The query with embedding to search for.
            number_of_results (int): The maximum number of results to return.
            filter (Optional[DocumentMetadataFilter]): Optional filter to apply to the query.

        Returns:
            List[QueryResult]: The list of query results.
        """
        collection = self._client.get_collection(collection_name)

        try:
            # ChromaDB expects embeddings as list[float], not list[list[float]]
            query_embeddings = query.embeddings[0]  # type: ignore[unreachable]
            response = collection.query(
                query_embeddings=query_embeddings,  # type: ignore[arg-type]
                n_results=number_of_results,  # ChromaDB API uses n_results, but we maintain our consistent interface
            )
            logging.info(f"Query response: {response}")
            return self._process_search_results(response, collection_name)
        except Exception as e:
            logging.error(f"Failed to query ChromaDB collection '{collection_name}': {e}")
            raise DocumentError(f"Failed to query ChromaDB collection '{collection_name}': {e}") from e

    def delete_collection(self, collection_name: str) -> None:
        """Deletes a collection from the vector store."""

        try:
            self._client.delete_collection(collection_name)
            logging.info(f"Deleted collection '{collection_name}'")
        except Exception as e:
            logging.error(f"Failed to delete ChromaDB collection: {e}")
            raise CollectionError(f"Failed to delete ChromaDB collection: {e}") from e

    def delete_documents(self, collection_name: str, document_ids: list[str]) -> None:
        """Deletes documents by their IDs from the vector store."""
        collection = self._client.get_collection(collection_name)

        try:
            collection.delete(ids=document_ids)
            logging.info(f"Deleted {len(document_ids)} documents from collection '{collection_name}'")
            return
        except Exception as e:
            logging.error(f"Failed to delete documents from ChromaDB collection '{collection_name}': {e}")
            raise DocumentError(f"Failed to delete documents from ChromaDB collection '{collection_name}': {e}") from e

    def _convert_to_chunk(self, id: str, text: str, embeddings: list[float] | None, metadata: dict) -> DocumentChunk:
        return DocumentChunk(
            chunk_id=id,
            text=text,
            embeddings=embeddings,
            metadata=DocumentChunkMetadata(
                source=Source(metadata["source"]) if metadata["source"] else Source.OTHER,
                document_id=metadata["document_id"],
            ),
            document_id=metadata["document_id"],
        )

    def _process_search_results(self, response: Any, collection_name: str) -> list[QueryResult]:  # noqa: ARG002
        results = []
        ids = response.get("ids", [[]])[0]
        distances = response.get("distances", [[]])[0]
        metadatas = response.get("metadatas", [[]])[0]
        documents = response.get("documents", [[]])[0]

        for i in range(len(ids)):
            chunk = self._convert_to_chunk(
                id=ids[i],
                text=documents[i],
                embeddings=None,  # Assuming embeddings are not returned in the response, otherwise add appropriate key
                metadata=metadatas[i],
            )
            results.append(QueryResult(chunk=chunk, score=1.0 - distances[i], embeddings=[]))
        return results
