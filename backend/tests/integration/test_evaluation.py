from typing import Any
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.orm import Session

from rag_solution.evaluation.evaluator import RAGEvaluator
from rag_solution.services.llm_provider_service import LLMProviderService
from rag_solution.services.question_service import QuestionService
from vectordbs.data_types import DocumentChunk, QueryResult


@pytest.fixture
def db_session() -> Mock:
    """Create a mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def llm_provider_service(db_session: Any) -> Mock:
    """Create a mock LLMProviderService instance."""
    return Mock(spec=LLMProviderService)


@pytest.fixture
def question_service(db_session: Any) -> Mock:
    """Create a mock QuestionService instance."""
    return Mock(spec=QuestionService)


@pytest.mark.integration
def test_rag_evaluator() -> None:
    """Test the RAGEvaluator."""
    evaluator = RAGEvaluator()
    assert evaluator is not None


def test_calculate_relevance_score() -> None:
    """Test the _calculate_relevance_score method."""
    evaluator = RAGEvaluator()
    query = "What is the theory of relativity?"
    retrieved_documents = [
        QueryResult(
            chunk=DocumentChunk(
                chunk_id="1",
                text="Albert Einstein's theory of relativity revolutionized our understanding of space, time, and gravity.",
            ),
            score=0.9,
            embeddings=[0.1, 0.2, 0.3],
        ),
        QueryResult(
            chunk=DocumentChunk(
                chunk_id="2",
                text="The theory of relativity consists of two parts: special relativity and general relativity.",
            ),
            score=0.8,
            embeddings=[0.4, 0.5, 0.6],
        ),
    ]
    relevance_score = evaluator._calculate_relevance_score(query, retrieved_documents)
    assert relevance_score >= 0 and relevance_score <= 1


def test_calculate_coherence_score() -> None:
    """Test the _calculate_coherence_score method."""
    evaluator = RAGEvaluator()
    query = "What is the theory of relativity?"
    response = "The theory of relativity, proposed by Albert Einstein, describes how space and time are interconnected and how gravity affects the fabric of spacetime."
    coherence_score = evaluator._calculate_coherence_score(query, response)
    assert coherence_score >= 0 and coherence_score <= 1


def test_calculate_faithfulness_score() -> None:
    """Test the _calculate_faithfulness_score method."""
    evaluator = RAGEvaluator()
    response = "The theory of relativity, proposed by Albert Einstein, describes how space and time are interconnected and how gravity affects the fabric of spacetime."
    retrieved_documents = [
        QueryResult(
            chunk=DocumentChunk(
                chunk_id="1",
                text="Albert Einstein's theory of relativity revolutionized our understanding of space, time, and gravity.",
            ),
            score=0.9,
            embeddings=[0.1, 0.2, 0.3],
        ),
        QueryResult(
            chunk=DocumentChunk(
                chunk_id="2",
                text="The theory of relativity consists of two parts: special relativity and general relativity.",
            ),
            score=0.8,
            embeddings=[0.4, 0.5, 0.6],
        ),
    ]
    faithfulness_score = evaluator._calculate_faithfulness_score(response, retrieved_documents)
    assert faithfulness_score >= 0 and faithfulness_score <= 1


@patch("rag_solution.evaluation.llm_as_judge_evals.init_llm")
async def test_evaluate(mock_init_llm: Any, llm_provider_service: Any, question_service: Any) -> None:
    """Test the evaluate method."""
    mock_init_llm.return_value = Mock()
    evaluator = RAGEvaluator()
    context = "This is the context."
    answer = "This is the answer."
    question = "What is the question?"
    evaluation_results = await evaluator.evaluate(context, answer, question)
    assert "faithfulness" in evaluation_results
    assert "answer_relevance" in evaluation_results
    assert "context_relevance" in evaluation_results


if __name__ == "__main__":
    pytest.main([__file__])
