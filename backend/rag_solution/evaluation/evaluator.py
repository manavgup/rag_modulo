from typing import List, Dict, Any
from vectordbs.data_types import QueryResult
from sklearn.metrics.pairwise import cosine_similarity
from vectordbs.utils.watsonx import get_embeddings
import logging
import asyncio
from vectordbs.utils.watsonx import get_embeddings
from rag_solution.evaluation.llm_as_judge_evals import FaithfulnessEvaluator,AnswerRelevanceEvaluator,ContextRelevanceEvaluator
from rag_solution.evaluation.llm_as_judge_evals import BASE_LLM_PARAMETERS, init_llm

logger = logging.getLogger(__name__)

class RAGEvaluator:
    def __init__(self):
        """
        Initialize the RAG Evaluator.
        """
        self.faithfulness_evaluator = FaithfulnessEvaluator()
        self.answer_relevance_evaluator = AnswerRelevanceEvaluator()
        self.context_relevance_evaluator = ContextRelevanceEvaluator()

    def evaluate_cosine(self, query: str, response: str, retrieved_documents: List[QueryResult]) -> Dict[str, float]:
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
        query_embedding = get_embeddings(query)
        doc_contents = [chunk.text for doc in retrieved_documents for chunk in doc.data or []]
        logger.info("Got document contents")
        doc_embeddings = get_embeddings(doc_contents)
        similarities = cosine_similarity(query_embedding, doc_embeddings)
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
        query_embedding = get_embeddings(query)
        response_embedding = get_embeddings(response)
        coherence = cosine_similarity(query_embedding, response_embedding)
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
        response_embedding = get_embeddings(response)
        doc_contents = [chunk.text for doc in retrieved_documents for chunk in doc.data or []]
        doc_embeddings = get_embeddings(doc_contents)
        similarities = cosine_similarity(response_embedding, doc_embeddings)
        return float(similarities.mean())

    async def evaluate(
        self,
        context: str,
        answer: str,
        question: str
    ) -> Dict[str, Any]:
        """
        Run all evaluators concurrently and collect their results.
        """
        try:
            llm = init_llm(parameters=BASE_LLM_PARAMETERS)
            results = await asyncio.gather(
                self.faithfulness_evaluator.a_evaluate(context=context, answer=answer, llm=llm),
                self.answer_relevance_evaluator.a_evaluate(question=question,answer=answer,llm=llm),
                self.context_relevance_evaluator.a_evaluate(context=context, question=question,llm=llm),
                return_exceptions=True
            )
            return {
                "faithfulness": results[0] if not isinstance(results[0], Exception) else f"Error: {results[0]}",
                "answer_relevance": results[1] if not isinstance(results[0], Exception) else f"Error: {results[1]}",
                "context_relevance": results[2] if not isinstance(results[2], Exception) else f"Error: {results[2]}",
            }
        except Exception as e:
            raise RuntimeError(f"Failed to run evaluations: {e}")
        finally:
            await llm.aclose_persistent_connection()

        return results

# Example usage
if __name__ == "__main__":
    from vectordbs.data_types import DocumentChunk
    from rag_solution.file_management.database import get_db
    from backend.rag_solution.services.search_service import SearchService
    from rag_solution.evaluation.qa import get_node_text


    evaluator = RAGEvaluator()
    # INITIAL COSINE METRICS
    query = "What is the theory of relativity?"
    response = "The theory of relativity, proposed by Albert Einstein, describes how space and time are interconnected and how gravity affects the fabric of spacetime."
    retrieved_documents = [
        QueryResult(data=[DocumentChunk(chunk_id='1',text="Albert Einstein's theory of relativity revolutionized our understanding of space, time, and gravity.", score=0.9)]),
        QueryResult(data=[DocumentChunk(chunk_id='2',text="The theory of relativity consists of two parts: special relativity and general relativity.", score=0.8)]),
    ]

    evaluation_results = evaluator.evaluate_cosine(query, response, retrieved_documents)
    print("Evaluation Results:")
    for metric, score in evaluation_results.items():
        print(f"{metric}: {score:.4f}")

    # Custom LLM as judge metrics
    db_session = next(get_db())
    from rag_solution.services.user_collection_service import UserCollectionService

    ucs = UserCollectionService(db=db_session)
    vdb_name = 'collection_8b1d4bc0a11b4f7c929b83d37e7b91d6'
    search_service = SearchService(db=db_session)
    pipeline = search_service.pipeline

    question = "What were the major equity-related activities reported by IBM as of December 31, 2023?"
    rag_response = """Based on the provided financial information, the major equity-related activities reported by IBM as of December 31, 2023 are:

    1. Net income: $1,639 million
    2. Other comprehensive income/(loss): $6,494 million
    3. Cash dividends paid—common stock: $(5,948) million
    4. Equity, December 31, 2023: $59,643 million

    Please note that the provided information is based on the IBM's Consolidated Statement of Equity as of December 31, 2023. If you need further clarification or details, please let me know. I'll do my best to assist you. Would you like me to provide more information or answer another question?"""

    retrieved_docs = pipeline.retriever.retrieve(vdb_name, question)
    ctx = retrieved_docs[0].data
    all_texts = [text.text for text in ctx]
    contexts = "\n****\n\n****\n".join([get_node_text(node=doc) for doc in ctx])

    evaluation_results = asyncio.run(evaluator.evaluate(context=contexts,answer=rag_response,question=question))
    print(f"Evaluation Results: {evaluation_results}")