from typing import List, Optional, Union, Dict, Any
from vectordbs.data_types import (
    Document, DocumentChunk, DocumentMetadataFilter, QueryWithEmbedding, 
    QueryResult, Source, DocumentChunkMetadata
)
from vectordbs.vector_store import VectorStore  
import logging
from chromadb import chromadb, ClientAPI, Collection
from vectordbs.utils.watsonx import get_embeddings, ChromaEmbeddingFunction
import os

CHROMADB_HOST = os.getenv("CHROMADB_HOST", "localhost")
CHROMADB_PORT = int(os.getenv("CHROMADB_PORT", "8000"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-MiniLM-L6-v2")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "384"))

logging.basicConfig(level=logging.INFO)

class ChromaDBStore(VectorStore):
    def __init__(self) -> None:
        self.collection_name :Optional[str] = None
        self.collection :Optional[Collection] = None
        
        try:
            self.client :ClientAPI = chromadb.HttpClient(
                host=CHROMADB_HOST,
                port=CHROMADB_PORT
            )
            logging.info("Connected to ChromaDB")
        except Exception as e:
            logging.error(f"Failed to connect to ChromaDB: {e}")
            raise

    def create_collection(self, collection_name: str, embedding_model: str = EMBEDDING_MODEL) -> None:
        try:
            if self.client:
                self.collection = self.client.get_or_create_collection(
                    name=collection_name,
                    embedding_function=ChromaEmbeddingFunction(model_id=embedding_model)
                )
                self.collection_name = collection_name
                print ("*** Collection Created: ", self.collection)
            else:
                logging.error("ChromaDB client not initialized")
                raise ValueError("ChromaDB client not initialized")
        except Exception as e:
            logging.error(f"Failed to create or retrieve ChromaDB collection: {e}")
            raise

    def add_documents(self, collection_name: str, documents: List[Document]) -> List[str]:
        if not self.collection or self.collection_name != collection_name:
            raise ValueError(f"Collection '{collection_name}' is not initialized")

        docs = []
        embeddings = []
        metadatas = []
        ids = []
        
        for document in documents:
            for chunk in document.chunks:
                docs.append(chunk.text)
                embeddings.append(chunk.vectors)
                metadatas.append(
                    {
                        "document_id": chunk.document_id,
                        "source": chunk.metadata.source.value if chunk.metadata else "",
                        "source_id": chunk.metadata.source_id if chunk.metadata else "",
                        "url": chunk.metadata.url if chunk.metadata else "",
                        "created_at": chunk.metadata.created_at if chunk.metadata else "",
                        "author": chunk.metadata.author if chunk.metadata else ""
                    }
                )
                ids.append(chunk.chunk_id)
        
        try:
            self.collection.upsert(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=docs
            )
            logging.info(f"Successfully added documents to collection '{collection_name}'")
            print("*** Collection Count: ", self.collection.count())
        except Exception as e:
            logging.error(f"Failed to add documents to ChromaDB collection '{collection_name}': {e}")
            raise
        
        return ids

    def retrieve_documents(self, query: Union[str, QueryWithEmbedding], collection_name: Optional[str] = None, limit: int = 10) -> List[QueryResult]:
        if isinstance(query, str):
            query_embeddings = get_embeddings(query)
            if not query_embeddings:
                raise ValueError("Failed to generate embeddings for the query string.")
            query = QueryWithEmbedding(text=query, vectors=query_embeddings)
        
        collection_name = collection_name or self.collection_name
        return self.query(collection_name, query, number_of_results=limit)

    def query(self, 
              collection_name: str, 
              query: QueryWithEmbedding,
              number_of_results: int = 10, 
              filter: Optional[DocumentMetadataFilter] = None) -> List[QueryResult]:
        try:
            if not self.collection or self.collection_name != collection_name:
                logging.error(f"Collection '{collection_name}' is not initialized")
                raise ValueError(f"Collection '{collection_name}' is not initialized")
            
            response = self.collection.query(
                query_embeddings=query.vectors, 
                n_results=number_of_results
            )
            print ("*** RESPONSE: ", response)
            logging.info(f"Query response: {response}")
            return self._process_search_results(response)
        except Exception as e:
            logging.error(f"Failed to query ChromaDB collection '{collection_name}': {e}")
            raise

    def delete_collection(self, collection_name: str) -> None:
        try:
            self.client.delete_collection(collection_name)
            self.collection = None
            logging.info(f"Deleted collection '{collection_name}'")
        except Exception as e:
            logging.error(f"Failed to delete ChromaDB collection: {e}")
            raise

    def delete_documents(self, document_ids: List[str], collection_name: Optional[str] = None) -> int:
        collection_name = collection_name or self.collection_name

        if not self.collection or self.collection_name != collection_name:
            logging.error(f"Collection '{collection_name}' is not initialized")
            return 0
        
        if not document_ids:
            logging.info("No document IDs provided for deletion")
            return 0

        try:
            self.collection.delete(ids=document_ids)
            deleted_count = len(document_ids)
            logging.info(f"Deleted {deleted_count} documents from collection '{collection_name}'")
            return deleted_count
        except Exception as e:
            logging.error(f"Failed to delete documents from ChromaDB collection '{collection_name}': {e}")
            return 0

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
                author=metadata["author"]
            ),
            document_id=metadata["document_id"]
        )

    def _process_search_results(self, response: Dict) -> List[QueryResult]:
        results = []
        ids = response.get('ids', [[]])[0]
        distances = response.get('distances', [[]])[0]
        metadatas = response.get('metadatas', [[]])[0]
        documents = response.get('documents', [[]])[0]

        for i in range(len(ids)):
            chunk = self._convert_to_chunk(
                id=ids[i],
                text=documents[i],
                vectors=None,  # Assuming vectors are not returned in the response, otherwise add appropriate key
                metadata=metadatas[i]
            )
            results.append(QueryResult(data=[chunk], similarities=[distances[i]], ids=[ids[i]]))
        return results

    def _build_filters(self, filter: Optional[DocumentMetadataFilter]) -> Dict[str, Any]:
        if not filter:
            return {}
        return {
            filter.field_name: filter.value
        }

    async def __aenter__(self) -> "ChromaDBStore":
        return self

    async def __aexit__(self, exc_type: Optional[type], exc_val: Optional[BaseException], exc_tb: Optional[Any]) -> None:
        pass
