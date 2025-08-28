import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session
from uuid import uuid4
from rag_solution.evaluation.evaluator import RAGEvaluator
from rag_solution.evaluation.llm_as_judge_evals import FaithfulnessEvaluator, AnswerRelevanceEvaluator, ContextRelevanceEvaluator
from rag_solution.services.llm_provider_service import LLMProviderService
from rag_solution.services.question_service import QuestionService
from rag_solution.schemas.question_schema import QuestionInput, QuestionOutput
from vectordbs.data_types import QueryResult, DocumentChunk

@pytest.fixture
def db_session():
    """Create a mock database session."""
    return Mock(spec=Session)

@pytest.fixture
def llm_provider_service(db_session):
    """Create a mock LLMProviderService instance."""
    return Mock(spec=LLMProviderService)

@pytest.fixture
def question_service(db_session):
    """Create a mock QuestionService instance."""
    return Mock(spec=QuestionService)

def test_rag_evaluator():
    """Test the RAGEvaluator."""
    evaluator = RAGEvaluator()
    assert evaluator is not None

def test_calculate_relevance_score():
    """Test the _calculate_relevance_score method."""
    evaluator = RAGEvaluator()
    query = "What is the theory of relativity?"
    retrieved_documents = [
        QueryResult(data=[DocumentChunk(chunk_id='1', text="Albert Einstein's theory of relativity revolutionized our understanding of space, time, and gravity.", score=0.9)]),
        QueryResult(data=[DocumentChunk(chunk_id='2', text="The theory of relativity consists of two parts: special relativity and general relativity.", score=0.8)]),
    ]
    relevance_score = evaluator._calculate_relevance_score(query, retrieved_documents)
    assert relevance_score >= 0 and relevance_score <= 1

def test_calculate_coherence_score():
    """Test the _calculate_coherence_score method."""
    evaluator = RAGEvaluator()
    query = "What is the theory of relativity?"
    response = "The theory of relativity, proposed by Albert Einstein, describes how space and time are interconnected and how gravity affects the fabric of spacetime."
    coherence_score = evaluator._calculate_coherence_score(query, response)
    assert coherence_score >= 0 and coherence_score <= 1

def test_calculate_faithfulness_score():
    """Test the _calculate_faithfulness_score method."""
    evaluator = RAGEvaluator()
    response = "The theory of relativity, proposed by Albert Einstein, describes how space and time are interconnected and how gravity affects the fabric of spacetime."
    retrieved_documents = [
        QueryResult(data=[DocumentChunk(chunk_id='1', text="Albert Einstein's theory of relativity revolutionized our understanding of space, time, and gravity.", score=0.9)]),
        QueryResult(data=[DocumentChunk(chunk_id='2', text="The theory of relativity consists of two parts: special relativity and general relativity.", score=0.8)]),
    ]
    faithfulness_score = evaluator._calculate_faithfulness_score(response, retrieved_documents)
    assert faithfulness_score >= 0 and faithfulness_score <= 1

@patch('rag_solution.evaluation.llm_as_judge_evals.init_llm')
async def test_evaluate(mock_init_llm, llm_provider_service, question_service):
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
