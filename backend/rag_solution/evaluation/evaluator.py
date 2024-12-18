from typing import List, Dict, Any
from vectordbs.data_types import QueryResult
from sklearn.metrics.pairwise import cosine_similarity
from vectordbs.utils.watsonx import get_embeddings
import logging

logger = logging.getLogger(__name__)

class RAGEvaluator:
    def __init__(self):
        """
        Initialize the RAG Evaluator.
        """
        pass

    def evaluate(self, query: str, response: str, retrieved_documents: List[QueryResult]) -> Dict[str, float]:
        """
        Evaluate the RAG pipeline results.

        Args:
            query (str): The original query.
            response (str): The generated response.
            retrieved_documents (List[QueryResult]): The list of retrieved documents.

        Returns:
            Dict[str, float]: A dictionary containing evaluation metrics.
        """
        relevance_score = self._calculate_relevance_score(query, retrieved_documents)
        coherence_score = self._calculate_coherence_score(query, response)
        faithfulness_score = self._calculate_faithfulness_score(response, retrieved_documents)

        return {
            "relevance": relevance_score,
            "coherence": coherence_score,
            "faithfulness": faithfulness_score,
            "overall_score": (relevance_score + coherence_score + faithfulness_score) / 3
        }

    def _calculate_relevance_score(self, query: str, retrieved_documents: List[QueryResult]) -> float:
        """
        Calculate the relevance score of retrieved documents to the query.

        Args:
            query (str): The original query.
            retrieved_documents (List[QueryResult]): The list of retrieved documents.

        Returns:
            float: The relevance score.
        """
        query_embedding = get_embeddings([query])
        doc_contents = [chunk.content for doc in retrieved_documents for chunk in doc.data or []]
        logger.info("Got document contents")
        doc_embeddings = get_embeddings(doc_contents)
        similarities = cosine_similarity([query_embedding], doc_embeddings)
        logger.info(f"Generated relevanace similarities: {similarities}")
        return float(similarities.mean())

    def _calculate_coherence_score(self, query: str, response: str) -> float:
        """
        Calculate the coherence score between the query and the response.

        Args:
            query (str): The original query.
            response (str): The generated response.

        Returns:
            float: The coherence score.
        """
        query_embedding = get_embeddings([query])
        response_embedding = get_embeddings([response])
        coherence = cosine_similarity([query_embedding], [response_embedding])
        return float(coherence)

    def _calculate_faithfulness_score(self, response: str, retrieved_documents: List[QueryResult]) -> float:
        """
        Calculate the faithfulness score of the response to the retrieved documents.

        Args:
            response (str): The generated response.
            retrieved_documents (List[QueryResult]): The list of retrieved documents.

        Returns:
            float: The faithfulness score.
        """
        response_embedding = get_embeddings([response])
        doc_contents = [chunk.content for doc in retrieved_documents for chunk in doc.data or []]
        doc_embeddings = get_embeddings(doc_contents)
        similarities = cosine_similarity([response_embedding], doc_embeddings)
        return float(similarities.mean())

# Example usage
if __name__ == "__main__":
    from vectordbs.data_types import DocumentChunk

    evaluator = RAGEvaluator()
    
    query = "What is the theory of relativity?"
    response = "The theory of relativity, proposed by Albert Einstein, describes how space and time are interconnected and how gravity affects the fabric of spacetime."
    retrieved_documents = [
        QueryResult(data=[DocumentChunk(content="Albert Einstein's theory of relativity revolutionized our understanding of space, time, and gravity.", score=0.9)]),
        QueryResult(data=[DocumentChunk(content="The theory of relativity consists of two parts: special relativity and general relativity.", score=0.8)]),
    ]

    evaluation_results = evaluator.evaluate(query, response, retrieved_documents)
    print("Evaluation Results:")
    for metric, score in evaluation_results.items():
        print(f"{metric}: {score:.4f}")
