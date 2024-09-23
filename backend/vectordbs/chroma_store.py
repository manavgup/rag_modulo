import logging
from typing import Dict, List, Mapping, Optional, Union

from chromadb import ClientAPI, chromadb

from core.config import settings
from vectordbs.utils.watsonx import get_embeddings

from .data_types import (Document, DocumentChunk, DocumentChunkMetadata,
                         DocumentMetadataFilter, QueryResult,
                         QueryWithEmbedding, Source)
from .error_types import CollectionError, DocumentError
from .vector_store import VectorStore

CHROMADB_HOST = settings.chromadb_host
CHROMADB_PORT = settings.chromadb_port
EMBEDDING_MODEL = settings.embedding_model
EMBEDDING_DIM = settings.embedding_dim

logging.basicConfig(level=settings.log_level)

MetadataType = Mapping[str, Union[str, int, float, bool]]

class ChromaDBStore(VectorStore):
    def __init__(self, client: Optional[ClientAPI] = None) -> None:
        self._client: ClientAPI = client or self._initialize_client()

    def _initialize_client(self) -> ClientAPI:
        """Initialize the ChromaDB client."""
        try:
            client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)
            logging.info("Connected to ChromaDB")
            return client
        except Exception as e:
            logging.error(f"Failed to connect to ChromaDB: {e}")
            raise CollectionError(f"Failed to connect to ChromaDB: {e}")

    def create_collection(self, collection_name: str, metadata: Optional[dict] = None) -> None:
        """Create a collection in ChromaDB."""
        try:
            self._client.create_collection(name=collection_name, metadata=metadata)
            logging.info(f"Collection '{collection_name}' created successfully")
        except Exception as e:
            logging.error(f"Failed to create collection '{collection_name}': {e}")
            raise CollectionError(f"Failed to create collection '{collection_name}': {e}")

    def add_documents(self, collection_name: str, documents: List[Document]) -> List[str]:
        """Adds documents to the vector store."""
        collection = self._client.get_collection(collection_name)
        self._initialize_client()
        self._initialize_collection(collection_name)

        docs, embeddings, metadatas, ids = [], [], [], []

        for document in documents:
            for chunk in document.chunks:
                docs.append(chunk.text)
                embeddings.append(chunk.vectors)
                metadata: MetadataType = {
                    "source": str(chunk.metadata.source),
                    "source_id": chunk.metadata.source_id or "",
                    "url": chunk.metadata.url or "",
                    "created_at": chunk.metadata.created_at or "",
                    "author": chunk.metadata.author or "",
                    "document_id": chunk.document_id or "",
                }
                metadatas.append(metadata)
                ids.append(chunk.chunk_id)

        try:
            collection.upsert(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=docs)
            logging.info(f"Successfully added documents to collection '{collection_name}'")
        except Exception as e:
            logging.error(f"Failed to add documents to ChromaDB collection '{collection_name}': {e}")
            raise DocumentError(f"Failed to add documents to ChromaDB collection '{collection_name}': {e}")

        return ids

    def retrieve_documents(
        self, query: str, collection_name: str, limit: int = 10
    ) -> List[QueryResult]:
        """Retrieves documents based on a query string."""
        query_embeddings = get_embeddings(query)
        if not query_embeddings:
            raise DocumentError("Failed to generate embeddings for the query string.")
        query_with_embedding = QueryWithEmbedding(text=query, vectors=query_embeddings)
        return self.query(collection_name, query_with_embedding, number_of_results=limit)

    def query(
        self, collection_name: str, query: QueryWithEmbedding,
        number_of_results: int = 10, filter: Optional[DocumentMetadataFilter] = None
    ) -> List[QueryResult]:
        """Queries the vector store with filtering and query mode options."""
        collection = self._get_collection(collection_name)

        try:
            response = collection.query(
                query_embeddings=query.vectors,
                n_results=number_of_results)
            logging.info(f"Query response: {response}")
            return self._process_search_results(response)
        except Exception as e:
            logging.error(f"Failed to query ChromaDB collection '{collection_name}': {e}")
            raise DocumentError(f"Failed to query ChromaDB collection '{collection_name}': {e}")

    def delete_collection(self, collection_name: str) -> None:
        """Deletes a collection from the vector store."""

        try:
            self._client.delete_collection(collection_name)
            logging.info(f"Deleted collection '{collection_name}'")
        except Exception as e:
            logging.error(f"Failed to delete ChromaDB collection: {e}")
            raise CollectionError(f"Failed to delete ChromaDB collection: {e}")

    def delete_documents(self, document_ids: List[str], collection_name: Optional[str] = None) -> int:
        """Deletes documents by their IDs from the vector store."""
        collection = self._get_collection(collection_name)

        try:
            deleted_count = collection.delete(ids=document_ids)
            logging.info(f"Deleted {deleted_count} documents from collection '{collection_name}'")
            return deleted_count
        except Exception as e:
            logging.error(f"Failed to delete documents from ChromaDB collection '{collection_name}': {e}")
            raise DocumentError(f"Failed to delete documents from ChromaDB collection '{collection_name}': {e}")

    def _convert_to_chunk(self, id: str, text: str, vectors: Optional[List[float]], metadata: Dict) -> DocumentChunk:
        return DocumentChunk(
            chunk_id=id,
            text=text,
            vectors=vectors,
            metadata=DocumentChunkMetadata(
                source=Source(metadata["source"]) if metadata["source"] else Source.OTHER,
                source_id=metadata["source_id"],
                url=metadata["url"],
                created_at=metadata["created_at"],
                author=metadata["author"],
            ),
            document_id=metadata["document_id"],
        )

    def _process_search_results(self, response: Dict) -> List[QueryResult]:
        results = []
        ids = response.get("ids", [[]])[0]
        distances = response.get("distances", [[]])[0]
        metadatas = response.get("metadatas", [[]])[0]
        documents = response.get("documents", [[]])[0]

        for i in range(len(ids)):
            chunk = self._convert_to_chunk(
                id=ids[i],
                text=documents[i],
                vectors=None,  # Assuming vectors are not returned in the response, otherwise add appropriate key
                metadata=metadatas[i],
            )
            results.append(QueryResult(data=[chunk], similarities=[distances[i]], ids=[ids[i]]))
        return results
