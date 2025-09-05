import asyncio
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sklearn.metrics.pairwise import cosine_similarity  # type: ignore[import-untyped]
else:
    try:
        from sklearn.metrics.pairwise import (
            cosine_similarity,  # type: ignore[import-untyped]
        )
    except ImportError:
        cosine_similarity = None

from rag_solution.evaluation.llm_as_judge_evals import (
    BASE_LLM_PARAMETERS,
    AnswerRelevanceEvaluator,
    ContextRelevanceEvaluator,
    FaithfulnessEvaluator,
    init_llm,
)
from vectordbs.data_types import DocumentChunk, QueryResult
from vectordbs.utils.watsonx import get_embeddings

logger = logging.getLogger(__name__)


class RAGEvaluator:
    def __init__(self) -> None:
        """Initialize the RAG Evaluator."""
        self.faithfulness_evaluator = FaithfulnessEvaluator()
        self.answer_relevance_evaluator = AnswerRelevanceEvaluator()
        self.context_relevance_evaluator = ContextRelevanceEvaluator()

    def evaluate_cosine(self, query: str, response: str, retrieved_documents: list[QueryResult]) -> dict[str, float]:
        """
        Evaluate the RAG pipeline results using cosine similarity.

        Args:
            query (str): The original query.
            response (str): The generated response.
            retrieved_documents (List[QueryResult]): The list of retrieved
                                                    documents.

        Returns:
            Dict[str, float]: A dictionary containing evaluation metrics.
        """
        if cosine_similarity is None:
            raise ImportError("scikit-learn is not installed. Please install it to use " "cosine similarity evaluation.")

        relevance_score = self._calculate_relevance_score(query, retrieved_documents)
        coherence_score = self._calculate_coherence_score(query, response)
        faithfulness_score = self._calculate_faithfulness_score(response, retrieved_documents)

        return {
            "relevance": relevance_score,
            "coherence": coherence_score,
            "faithfulness": faithfulness_score,
            "overall_score": (relevance_score + coherence_score + faithfulness_score) / 3,
        }

    def _calculate_relevance_score(self, query: str, retrieved_documents: list[QueryResult]) -> float:
        """
        Calculate the relevance score of retrieved documents to the query.

        Args:
            query (str): The original query.
            retrieved_documents (List[QueryResult]): The list of retrieved
                                                    documents.

        Returns:
            float: The relevance score.
        """
        query_embedding = get_embeddings(query)
        # Extract text from document chunks
        doc_contents = [doc.chunk.text for doc in retrieved_documents]
        logger.info("Got document contents")
        doc_embeddings = get_embeddings(doc_contents)
        similarities = cosine_similarity(query_embedding, doc_embeddings)
        logger.info(f"Generated relevance similarities: {similarities}")
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

    def _calculate_faithfulness_score(self, response: str, retrieved_documents: list[QueryResult]) -> float:
        """
        Calculate the faithfulness score of the response to the retrieved
        documents.

        Args:
            response (str): The generated response.
            retrieved_documents (List[QueryResult]): The list of retrieved
                                                    documents.

        Returns:
            float: The faithfulness score.
        """
        response_embedding = get_embeddings(response)
        doc_contents = [doc.chunk.text for doc in retrieved_documents]
        doc_embeddings = get_embeddings(doc_contents)
        similarities = cosine_similarity(response_embedding, doc_embeddings)
        return float(similarities.mean())

    async def evaluate(self, context: str, answer: str, question: str) -> dict[str, Any]:
        """
        Run all LLM-as-a-judge evaluators concurrently and collect their results.

        Returns:
            Dict[str, Any]: A dictionary containing evaluation results.
        """
        llm = None
        try:
            llm = init_llm(parameters=BASE_LLM_PARAMETERS)
            results = await asyncio.gather(
                self.faithfulness_evaluator.a_evaluate_faithfulness(context=context, answer=answer, llm=llm),
                self.answer_relevance_evaluator.a_evaluate_answer_relevance(question=question, answer=answer, llm=llm),
                self.context_relevance_evaluator.a_evaluate_context_relevance(context=context, question=question, llm=llm),
                return_exceptions=True,
            )
            return {
                "faithfulness": (results[0] if not isinstance(results[0], Exception) else f"Error: {results[0]}"),
                "answer_relevance": (results[1] if not isinstance(results[1], Exception) else f"Error: {results[1]}"),
                "context_relevance": (results[2] if not isinstance(results[2], Exception) else f"Error: {results[2]}"),
            }
        except Exception as e:
            logger.error(f"Failed to run evaluations: {e}", exc_info=True)
            raise RuntimeError(f"Failed to run evaluations: {e}") from e
        finally:
            if llm:
                await llm.aclose_persistent_connection()


# Example usage
if __name__ == "__main__":
    # Mock function since the module doesn't exist
    def get_node_text(node: Any) -> str:
        return getattr(node, "text", str(node))

    from rag_solution.file_management.database import get_db
    from rag_solution.services.search_service import SearchService
    from rag_solution.services.user_collection_service import UserCollectionService

    evaluator = RAGEvaluator()

    # INITIAL COSINE METRICS
    print("--- Evaluating Cosine Metrics ---")
    query = "What is the theory of relativity?"
    response = "The theory of relativity, proposed by Albert Einstein, " "describes how space and time are interconnected and how gravity " "affects the fabric of spacetime."
    retrieved_documents = [
        QueryResult(
            chunk=DocumentChunk(
                chunk_id="1",
                text=("Albert Einstein's theory of relativity " "revolutionized our understanding of space, time, " "and gravity."),
                metadata=None,
            ),
            score=0.9,
            embeddings=[0.1, 0.2, 0.3],  # Mock embeddings
        ),
        QueryResult(
            chunk=DocumentChunk(
                chunk_id="2",
                text=("The theory of relativity consists of two parts: " "special relativity and general relativity."),
                metadata=None,
            ),
            score=0.8,
            embeddings=[0.4, 0.5, 0.6],  # Mock embeddings
        ),
    ]

    evaluation_results_cosine = evaluator.evaluate_cosine(query, response, retrieved_documents)
    print("Evaluation Results (Cosine Similarity):")
    for metric, score in evaluation_results_cosine.items():
        print(f"  {metric}: {score:.4f}")

    # Custom LLM-as-a-judge metrics
    print("\n--- Evaluating LLM-as-a-Judge Metrics ---")
    db_session = next(get_db())
    user_collection_service = UserCollectionService(db=db_session)
    vector_database_name = "collection_8b1d4bc0a11b4f7c929b83d37e7b91d6"
    search_service = SearchService(db=db_session)
    pipeline = search_service._pipeline_service

    question = "What were the major equity-related activities reported by IBM as " "of December 31, 2023?"
    rag_response = (
        "Based on the provided financial information, the major equity-"
        "related activities reported by IBM as of December 31, 2023 are:\n\n"
        "1. Net income: $1,639 million\n"
        "2. Other comprehensive income/(loss): $6,494 million\n"
        "3. Cash dividends paid—common stock: $(5,948) million\n"
        "4. Equity, December 31, 2023: $59,643 million\n\n"
        "Please note that the provided information is based on the IBM's "
        "Consolidated Statement of Equity as of December 31, 2023. If you "
        "need further clarification or details, please let me know. I'll "
        "do my best to assist you. Would you like me to provide more "
        "information or answer another question?"
    )

    if pipeline is None:
        raise ValueError("Pipeline service not available")

    from vectordbs.data_types import VectorQuery

    vector_query = VectorQuery(text=question, number_of_results=5)
    retrieved_docs = pipeline.retriever.retrieve(vector_database_name, vector_query)
    # QueryResult has a `chunk` attribute, not `data`
    context_data = [retrieved_docs[0].chunk] if retrieved_docs else []
    contexts = "\n****\n\n****\n".join([get_node_text(node=doc) for doc in context_data])

    evaluation_results_llm = asyncio.run(evaluator.evaluate(context=contexts, answer=rag_response, question=question))
    print(f"Evaluation Results (LLM-as-a-Judge): " f"{evaluation_results_llm}")
