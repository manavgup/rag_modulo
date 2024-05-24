from typing import List, Optional
import pinecone
import numpy as np
from vectordbs.vector_store import VectorStore  # Ensure this import is correct

class PineconeStore(VectorStore):
    def __init__(self, api_key: str, environment: str, index_name: str):
        pinecone.init(api_key=api_key, environment=environment)
        self.index_name = index_name
        self.index = pinecone.Index(self.index_name)

    def create_collection(self, name: str, dim: int, metadata_configs: Optional[dict] = None):
        """
        Create a new Pinecone index.

        Args:
            name (str): The name of the index to create.
            dim (int): The dimension of the vectors.
            metadata_configs (Optional[dict]): Custom metadata configurations for the index.
        """
        if name not in pinecone.list_indexes():
            pinecone.create_index(name, dimension=dim, metadata_configs=metadata_configs)
            self.index = pinecone.Index(name)

    def delete_collection(self, name: str):
        """
        Delete an existing Pinecone index.

        Args:
            name (str): The name of the index to delete.
        """
        if name in pinecone.list_indexes():
            pinecone.delete_index(name)

    def add_documents(self, collection_name: str, documents: List[dict]):
        """
        Add a list of documents to the index.

        Args:
            collection_name (str): The name of the index to add documents to.
            documents (List[dict]): The list of documents to add.
                Each document should be a dictionary with 'text' and 'embedding' keys.
        """
        ids = [doc.get('id', str(i)) for i, doc in enumerate(documents)]
        embeddings = [doc['embedding'] for doc in documents]
        metadata = [doc.get('metadata', {}) for doc in documents]
        self.index.upsert(ids=ids, vectors=embeddings, metadata=metadata)

    def retrieve_documents(self, collection_name: str, search_query: List[float], top_k: int = 10):
        """
        Retrieve documents from the index.

        Args:
            collection_name (str): The name of the index to retrieve documents from.
            search_query (List[float]): The search query (vector) to filter documents.
            top_k (int): The maximum number of results to return (default: 10).

        Returns:
            List[dict]: The list of retrieved documents.
        """
        query_vector = np.array(search_query).astype(np.float32)
        results = self.index.query(query_vector, top_k=top_k, include_metadata=True)

        retrieved_documents = []
        for match in results["matches"]:
            retrieved_documents.append({
                "id": match["id"],
                "score": match["score"],
                "text": match["metadata"].get("text", ""),
                "embedding": match["values"],
                "metadata": match["metadata"]
            })

        return retrieved_documents

    def delete_data(self, collection_name: str, document_ids: List[str]):
        """
        Delete documents from the index by their IDs.

        Args:
            collection_name (str): The name of the index to delete data from.
            document_ids (List[str]): The list of document IDs to delete.
        """
        self.index.delete(ids=document_ids)