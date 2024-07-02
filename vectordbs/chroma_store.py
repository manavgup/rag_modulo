import asyncio
import logging
from typing import Any, Dict, List, Optional

from chromadb import ClientAPI, Collection, chromadb

from vectordbs.data_types import (
    Document, DocumentChunk, DocumentChunkMetadata,
    DocumentMetadataFilter, QueryResult, QueryWithEmbedding, Source
)
from vectordbs.utils.watsonx import ChromaEmbeddingFunction, get_embeddings
from vectordbs.vector_store import VectorStore
from vectordbs.error_types import CollectionError, DocumentError
from config import settings

CHROMADB_HOST = settings.chromadb_host
CHROMADB_PORT = settings.chromadb_port
EMBEDDING_MODEL = settings.embedding_model
EMBEDDING_DIM = settings.embedding_dim

logging.basicConfig(level=settings.log_level)


class ChromaDBStore(VectorStore):
    def __init__(self) -> None:
        self._client: Optional[ClientAPI] = None
        self.collection_name: Optional[str] = None
        self.collection: Optional[Collection] = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        if self._client is None:
            try:
                self._client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)
                logging.info("Connected to ChromaDB")
            except Exception as e:
                logging.error(f"Failed to connect to ChromaDB: {e}")
                raise CollectionError(f"Failed to connect to ChromaDB: {e}")

    def _initialize_collection(self, collection_name: str) -> None:
        if self.collection_name != collection_name:
            raise CollectionError(f"Collection '{collection_name}' is not initialized")

    async def create_collection_async(self, collection_name: str, metadata: Optional[dict] = None) -> None:
        """Creates a collection in the vector store asynchronously."""
        self._initialize_client()
        try:
            if self._client is None:
                raise CollectionError("ChromaDB client is not initialized")
            self.collection = await asyncio.to_thread(
                self._client.get_or_create_collection,
                name=collection_name,
                embedding_function=ChromaEmbeddingFunction(
                    model_id=metadata.get("embedding_model", EMBEDDING_MODEL)
                    if metadata else EMBEDDING_MODEL,
                ),
            )
            self.collection_name = collection_name
            logging.info(f"Collection created: {self.collection}")
        except Exception as e:
            logging.error(f"Failed to create or retrieve ChromaDB collection: {e}")
            raise CollectionError(f"Failed to create or retrieve ChromaDB collection: {e}")

    async def add_documents_async(self, collection_name: str, documents: List[Document]) -> List[str]:
        """Adds documents to the vector store asynchronously."""
        self._initialize_client()
        self._initialize_collection(collection_name)

        docs, embeddings, metadatas, ids = [], [], [], []

        for document in documents:
            for chunk in document.chunks:
                docs.append(chunk.text)
                embeddings.append(chunk.vectors)
                metadatas.append({
                    "document_id": document.document_id, #each chunk belongs to its parent
                    "source": chunk.metadata.source.value if chunk.metadata else "",
                    "source_id": chunk.metadata.source_id if chunk.metadata else "",
                    "url": chunk.metadata.url if chunk.metadata else "",
                    "created_at": chunk.metadata.created_at if chunk.metadata else "",
                    "author": chunk.metadata.author if chunk.metadata else "",
                })
                ids.append(chunk.chunk_id)

        try:
            await asyncio.to_thread(
                self.collection.upsert, 
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=docs)
            logging.info(f"Successfully added documents to collection '{collection_name}'")
        except Exception as e:
            logging.error(f"Failed to add documents to ChromaDB collection '{collection_name}': {e}")
            raise DocumentError(f"Failed to add documents to ChromaDB collection '{collection_name}': {e}")

        return ids

    async def retrieve_documents_async(
        self, query: str, collection_name: Optional[str] = None, limit: int = 10
    ) -> List[QueryResult]:
        """Retrieves documents asynchronously based on a query string."""
        query_embeddings = get_embeddings(query)
        if not query_embeddings:
            raise DocumentError("Failed to generate embeddings for the query string.")
        query_with_embedding = QueryWithEmbedding(text=query, vectors=query_embeddings)
        return await self.query_async(collection_name, query_with_embedding, number_of_results=limit)

    async def query_async(
        self, collection_name: str, query: QueryWithEmbedding, number_of_results: int = 10, filter: Optional[DocumentMetadataFilter] = None
    ) -> List[QueryResult]:
        """Queries the vector store with filtering and query mode options asynchronously."""
        self._initialize_client()
        self._initialize_collection(collection_name)
        if not self.collection:
            raise CollectionError(f"Collection '{collection_name}' is not initialized.")

        try:
            response = await asyncio.to_thread(
                self.collection.query,
                query_embeddings=query.vectors,
                n_results=number_of_results)
            logging.info(f"Query response: {response}")
            return self._process_search_results(response)
        except Exception as e:
            logging.error(f"Failed to query ChromaDB collection '{collection_name}': {e}")
            raise DocumentError(f"Failed to query ChromaDB collection '{collection_name}': {e}")

    async def delete_collection_async(self, collection_name: str) -> None:
        """Deletes a collection from the vector store asynchronously."""
        self._initialize_client()
        self._initialize_collection(collection_name)

        try:
            await asyncio.to_thread(self._client.delete_collection, collection_name)
            self.collection = None
            self.collection_name = None
            logging.info(f"Deleted collection '{collection_name}'")
        except Exception as e:
            logging.error(f"Failed to delete ChromaDB collection: {e}")
            raise CollectionError(f"Failed to delete ChromaDB collection: {e}")

    async def delete_documents_async(self, document_ids: List[str], collection_name: Optional[str] = None) -> int:
        """Deletes documents by their IDs from the vector store asynchronously."""
        self._initialize_client()
        self._initialize_collection(collection_name)

        if not document_ids:
            logging.info("No document IDs provided for deletion")
            return 0

        try:
            await asyncio.to_thread(self.collection.delete, ids=document_ids)
            deleted_count = len(document_ids)
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

    async def __aenter__(self) -> "ChromaDBStore":
        self._initialize_client()
        return self

    async def __aexit__(self, exc_type: Optional[type], exc_val: Optional[BaseException], exc_tb: Optional[Any]) -> None:
        self._client = None
        self.collection = None
        self.collection_name = None
