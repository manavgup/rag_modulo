"""RAG Evaluation Module.

This module provides comprehensive evaluation capabilities for RAG (Retrieval-Augmented Generation)
systems using both traditional metrics (cosine similarity) and LLM-as-a-judge evaluation methods.
It includes evaluators for faithfulness, answer relevance, and context relevance.
"""

import asyncio
import logging
import sys
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

# Import evaluation dependencies if available, otherwise handle gracefully
try:
    from rag_solution.evaluation.llm_as_judge_evals import (
        BASE_LLM_PARAMETERS,
        AnswerRelevanceEvaluator,
        ContextRelevanceEvaluator,
        FaithfulnessEvaluator,
        init_llm,
    )
except ImportError:
    # Handle case where llm_as_judge_evals is not available
    BASE_LLM_PARAMETERS = None
    AnswerRelevanceEvaluator = None
    ContextRelevanceEvaluator = None
    FaithfulnessEvaluator = None
    init_llm = None

try:
    from vectordbs.data_types import DocumentChunkWithScore, QueryResult, VectorQuery
    from vectordbs.utils.watsonx import get_embeddings
except ImportError:
    # Handle case where vectordbs is not available
    DocumentChunkWithScore = None
    QueryResult = None
    VectorQuery = None
    get_embeddings = None

logger = logging.getLogger(__name__)


class RAGEvaluator:
    """RAG Evaluation System.

    This class provides comprehensive evaluation capabilities for RAG systems,
    including cosine similarity-based metrics and LLM-as-a-judge evaluations
    for faithfulness, answer relevance, and context relevance.
    """

    def __init__(self) -> None:
        """Initialize the RAG Evaluator."""
        self.faithfulness_evaluator = FaithfulnessEvaluator()
        self.answer_relevance_evaluator = AnswerRelevanceEvaluator()
        self.context_relevance_evaluator = ContextRelevanceEvaluator()

    def evaluate_cosine(
        self, query_text: str, response_text: str, document_list: list[QueryResult]
    ) -> dict[str, float]:
        """
        Evaluate the RAG pipeline results using cosine similarity.

        Args:
            query_text (str): The original query.
            response_text (str): The generated response.
            document_list (List[QueryResult]): The list of retrieved documents.

        Returns:
            Dict[str, float]: A dictionary containing evaluation metrics.
        """
        if cosine_similarity is None:
            raise ImportError("scikit-learn is not installed. Please install it to use cosine similarity evaluation.")

        relevance_score = self._calculate_relevance_score(query_text, document_list)
        coherence_score = self._calculate_coherence_score(query_text, response_text)
        faithfulness_score = self._calculate_faithfulness_score(response_text, document_list)

        return {
            "relevance": relevance_score,
            "coherence": coherence_score,
            "faithfulness": faithfulness_score,
            "overall_score": (relevance_score + coherence_score + faithfulness_score) / 3,
        }

    def _calculate_relevance_score(self, query_text: str, document_list: list[QueryResult]) -> float:
        """
        Calculate the relevance score of retrieved documents to the query.

        Args:
            query_text (str): The original query.
            document_list (List[QueryResult]): The list of retrieved documents.

        Returns:
            float: The relevance score.
        """
        query_embedding = get_embeddings(query_text)
        # Extract text from document chunks
        doc_contents = [doc.chunk.text for doc in document_list]
        logger.info("Got document contents")
        doc_embeddings = get_embeddings(doc_contents)
        similarities = cosine_similarity(query_embedding, doc_embeddings)
        logger.info("Generated relevance similarities: %s", similarities)
        return float(similarities.mean())

    def _calculate_coherence_score(self, query_text: str, response_text: str) -> float:
        """
        Calculate the coherence score between the query and the response.

        Args:
            query_text (str): The original query.
            response_text (str): The generated response.

        Returns:
            float: The coherence score.
        """
        query_embedding = get_embeddings(query_text)
        response_embedding = get_embeddings(response_text)
        coherence = cosine_similarity(query_embedding, response_embedding)
        # Handle both scalar and array results from cosine_similarity
        if hasattr(coherence, "item"):
            return float(coherence.item())
        return float(coherence)

    def _calculate_faithfulness_score(self, response_text: str, document_list: list[QueryResult]) -> float:
        """
        Calculate the faithfulness score of the response to the retrieved documents.

        Args:
            response_text (str): The generated response.
            document_list (List[QueryResult]): The list of retrieved documents.

        Returns:
            float: The faithfulness score.
        """
        response_embedding = get_embeddings(response_text)
        doc_contents = [doc.chunk.text for doc in document_list]
        doc_embeddings = get_embeddings(doc_contents)
        similarities = cosine_similarity(response_embedding, doc_embeddings)
        return float(similarities.mean())

    async def evaluate(self, context: str, answer: str, question_text: str) -> dict[str, Any]:
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
                self.answer_relevance_evaluator.a_evaluate_answer_relevance(
                    question=question_text, answer=answer, llm=llm
                ),
                self.context_relevance_evaluator.a_evaluate_context_relevance(
                    context=context, question=question_text, llm=llm
                ),
                return_exceptions=True,
            )
            return {
                "faithfulness": (results[0] if not isinstance(results[0], Exception) else f"Error: {results[0]}"),
                "answer_relevance": (results[1] if not isinstance(results[1], Exception) else f"Error: {results[1]}"),
                "context_relevance": (results[2] if not isinstance(results[2], Exception) else f"Error: {results[2]}"),
            }
        except Exception as e:
            logger.error("Failed to run evaluations: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to run evaluations: {e}") from e
        finally:
            if llm:
                await llm.aclose_persistent_connection()


# Example usage
if __name__ == "__main__":
    # Mock function since the module doesn't exist
    def get_node_text(node: Any) -> str:
        """Extract text from node."""
        return getattr(node, "text", str(node))

    # Import dependencies that may not be available
    try:
        from core.config import get_settings
        from rag_solution.file_management.database import get_db  # pylint: disable=ungrouped-imports
        from rag_solution.services.search_service import SearchService
        from rag_solution.services.user_collection_service import UserCollectionService
    except ImportError:
        print("Required dependencies not available for example usage")
        sys.exit(1)

    evaluator = RAGEvaluator()

    # INITIAL COSINE METRICS
    print("--- Evaluating Cosine Metrics ---")
    SAMPLE_QUERY = "What is the theory of relativity?"
    SAMPLE_RESPONSE = (
        "The theory of relativity, proposed by Albert Einstein, "
        "describes how space and time are interconnected and how gravity "
        "affects the fabric of spacetime."
    )
    SAMPLE_RETRIEVED_DOCUMENTS = [
        QueryResult(
            chunk=DocumentChunkWithScore(
                chunk_id="1",
                text=(
                    "Albert Einstein's theory of relativity "
                    "revolutionized our understanding of space, time, and gravity."
                ),
                metadata=None,
                score=0.9,
            ),
            score=0.9,
            embeddings=[0.1, 0.2, 0.3],  # Mock embeddings
        ),
        QueryResult(
            chunk=DocumentChunkWithScore(
                chunk_id="2",
                text=("The theory of relativity consists of two parts: special relativity and general relativity."),
                metadata=None,
                score=0.8,
            ),
            score=0.8,
            embeddings=[0.4, 0.5, 0.6],  # Mock embeddings
        ),
    ]

    evaluation_results_cosine = evaluator.evaluate_cosine(SAMPLE_QUERY, SAMPLE_RESPONSE, SAMPLE_RETRIEVED_DOCUMENTS)
    print("Evaluation Results (Cosine Similarity):")
    for metric, score in evaluation_results_cosine.items():
        print(f"  {metric}: {score:.4f}")

    # Custom LLM-as-a-judge metrics
    print("\n--- Evaluating LLM-as-a-Judge Metrics ---")
    db_session = next(get_db())
    settings = get_settings()
    user_collection_service = UserCollectionService(db=db_session)
    VECTOR_DATABASE_NAME = "collection_8b1d4bc0a11b4f7c929b83d37e7b91d6"
    search_service = SearchService(db=db_session, settings=settings)
    pipeline = search_service._pipeline_service  # pylint: disable=protected-access

    SAMPLE_QUESTION = "What were the major equity-related activities reported by IBM as of December 31, 2023?"
    SAMPLE_RAG_RESPONSE = (
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

    vector_query = VectorQuery(text=SAMPLE_QUESTION, number_of_results=5)
    retrieved_docs = pipeline.retriever.retrieve(VECTOR_DATABASE_NAME, vector_query)
    # QueryResult has a `chunk` attribute, not `data`
    context_data = [retrieved_docs[0].chunk] if retrieved_docs else []
    SAMPLE_CONTEXTS = "\n****\n\n****\n".join([get_node_text(node=doc) for doc in context_data])

    evaluation_results_llm = asyncio.run(
        evaluator.evaluate(context=SAMPLE_CONTEXTS, answer=SAMPLE_RAG_RESPONSE, question_text=SAMPLE_QUESTION)
    )
    print(f"Evaluation Results (LLM-as-a-Judge): {evaluation_results_llm}")
