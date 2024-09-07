from typing import List, Dict, Any
from abc import ABC, abstractmethod
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from backend.vectordbs.utils.watsonx import generate_text
from backend.core.config import settings

class BaseRetriever(ABC):
    @abstractmethod
    def retrieve(self, query: str, k: int = 10) -> List[Dict[str, Any]]:
        pass

class VectorRetriever(BaseRetriever):
    def __init__(self, vector_store):
        self.vector_store = vector_store
        self.model = settings.embedding_model

    def retrieve(self, query: str, k: int = 10) -> List[Dict[str, Any]]:
        query_embedding = self.model.encode([query])[0]
        results = self.vector_store.search(query_embedding, k=k)
        return [{"id": r.id, "content": r.payload['content'], "score": r.score} for r in results]

class KeywordRetriever(BaseRetriever):
    def __init__(self, documents: List[Dict[str, Any]]):
        self.documents = documents
        self.vectorizer = TfidfVectorizer()
        self.tfidf_matrix = self.vectorizer.fit_transform([doc['content'] for doc in documents])

    def retrieve(self, query: str, k: int = 10) -> List[Dict[str, Any]]:
        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        top_k_indices = similarities.argsort()[-k:][::-1]
        return [
            {"id": self.documents[i]['id'],
             "content": self.documents[i]['content'],
             "score": similarities[i]}
            for i in top_k_indices
        ]

class HybridRetriever(BaseRetriever):
    def __init__(self, vector_store, documents: List[Dict[str, Any]], vector_weight: float = 0.7):
        self.vector_retriever = VectorRetriever(vector_store)
        self.keyword_retriever = KeywordRetriever(documents)
        self.vector_weight = vector_weight

    def retrieve(self, query: str, k: int = 10) -> List[Dict[str, Any]]:
        vector_results = self.vector_retriever.retrieve(query, k=k)
        keyword_results = self.keyword_retriever.retrieve(query, k=k)
        
        # Combine and re-rank results
        combined_results = {}
        for result in vector_results + keyword_results:
            if result['id'] in combined_results:
                combined_results[result['id']]['score'] += self.vector_weight * result['score']
            else:
                combined_results[result['id']] = result
                combined_results[result['id']]['score'] *= self.vector_weight

        ranked_results = sorted(combined_results.values(), key=lambda x: x['score'], reverse=True)
        return ranked_results[:k]

class Retriever:
    def __init__(self, config: Dict[str, Any], vector_store, documents: List[Dict[str, Any]]):
        if config.get('use_hybrid', True):
            self.retriever = HybridRetriever(vector_store, documents, config.get('vector_weight', 0.7))
        elif config.get('use_vector', True):
            self.retriever = VectorRetriever(vector_store)
        else:
            self.retriever = KeywordRetriever(documents)

    def retrieve(self, query: str, k: int = 10) -> List[Dict[str, Any]]:
        return self.retriever.retrieve(query, k)

# Example usage
if __name__ == "__main__":
    from backend.vectordbs.factory import get_vectorstore
    
    # Initialize vector store and documents
    vector_store = get_vectorstore('milvus')  # Or any other supported vector store
    documents = [
        {"id": 1, "content": "Einstein developed the theory of relativity."},
        {"id": 2, "content": "Newton discovered the laws of motion and universal gravitation."},
        # Add more documents...
    ]

    config = {'use_hybrid': True, 'vector_weight': 0.7}
    retriever = Retriever(config, vector_store, documents)
    
    query = "Who developed the theory of relativity?"
    results = retriever.retrieve(query, k=5)
    
    for result in results:
        print(f"ID: {result['id']}, Score: {result['score']}, Content: {result['content']}")