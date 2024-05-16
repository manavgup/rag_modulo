import chromadb
from chromadb.api.types import Documents, Embeddings, EmbeddingFunction
from chromadb import Collection, QueryResult
from typing import Optional

from genai.schema import TextEmbeddingParameters
from genai import Client
from vector_store import VectorStore

class ChromaEmbeddingFunction(EmbeddingFunction):
    def __init__(self, *, model_id: str, client: Client, parameters: Optional[TextEmbeddingParameters] = None):
        self._model_id = model_id
        self._parameters = parameters
        self._client = client
        
    def __call__(self, inputs: Documents) -> Embeddings:
        embeddings: Embeddings = []
        for response in self._client.text.embedding.create(
            model_id=self._model_id, inputs=inputs, parameters=self._parameters
        ):
            embeddings.extend(response.results)

        return embeddings
    
    
class ChromaDBStore(VectorStore):
    def __init__(self, path: str):
        self.db = chromadb.PersistentClient(path=path)
        self.collection :Optional[Collection] = None
        
    def embed_with_watsonx(self, 
                inputs: Documents,
                client: Client,
                model_id: str,
                parameters: Optional[TextEmbeddingParameters] = None) -> Embeddings:
        embeddings: Embeddings = []
        for response in client.text.embedding.create(
            model_id=model_id, inputs=inputs, parameters=parameters
        ):
            embeddings.extend(response.results)

        return embeddings

    def create_collection(self, name: str, embedding_model_id: str, client: Client, create_new: bool = False):
        self.collection = self.db.get_or_create_collection(name=name, 
                                embedding_function=ChromaEmbeddingFunction(model_id=embedding_model_id, client=client))
        return self.collection
    
    def delete_collection(self, name: str):
        self.db.delete_collection(name=name)

    def add_documents(self, collection_name: str, documents: Documents):
        if self.collection is None or self.collection.name != collection_name:
            self.collection = self.db.get_collection(collection_name)
        self.collection.add(documents)

    def retrieve_documents(self, collection_name: str, query: str) -> QueryResult:
        if self.collection is None or self.collection.name != collection_name:
            self.collection = self.db.get_collection(collection_name)         
        return self.collection.query(query_texts=[query])

    def delete_data(self, collection_name: str, criteria: str):
        collection :Collection = self.db.get_collection(collection_name)
        
        if collection is not None:
            result: QueryResult = collection.query(query_texts=[criteria])
            if result is not None:
                for id in result["ids"]:
                    collection.delete(id)
    
