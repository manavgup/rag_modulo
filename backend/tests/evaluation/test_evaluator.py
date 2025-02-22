import pytest
import numpy as np
from unittest.mock import patch, AsyncMock, MagicMock
from rag_solution.evaluation.evaluator import RAGEvaluator
from vectordbs.data_types import QueryResult, DocumentChunk
from rag_solution.evaluation.llm_as_judge_evals import (
    FaithfulnessEvaluator,
    AnswerRelevanceEvaluator,
    ContextRelevanceEvaluator
)

@pytest.fixture
def evaluator():
    """Create a RAGEvaluator instance."""
    return RAGEvaluator()

@pytest.fixture
def sample_query_result():
    """Create sample query results."""
    return [
        QueryResult(data=[
            DocumentChunk(
                chunk_id='1',
                text="Einstein's theory of relativity revolutionized physics.",
                score=0.9
            ),
            DocumentChunk(
                chunk_id='2',
                text="The theory describes the relationship between space and time.",
                score=0.8
            )
        ]),
        QueryResult(data=[
            DocumentChunk(
                chunk_id='3',
                text="General relativity explains gravity as curved spacetime.",
                score=0.7
            )
        ])
    ]

def test_evaluator_initialization(evaluator):
    """Test RAGEvaluator initialization."""
    assert isinstance(evaluator.faithfulness_evaluator, FaithfulnessEvaluator)
    assert isinstance(evaluator.answer_relevance_evaluator, AnswerRelevanceEvaluator)
    assert isinstance(evaluator.context_relevance_evaluator, ContextRelevanceEvaluator)

def test_evaluate_cosine(evaluator, sample_query_result):
    """Test the evaluate_cosine method."""
    query = "What is the theory of relativity?"
    response = "The theory of relativity describes space, time, and gravity."
    
    # Mock embeddings to return consistent values
    mock_embeddings = np.array([[1.0, 0.0], [0.8, 0.2]])
    
    with patch('rag_solution.evaluation.evaluator.get_embeddings', return_value=mock_embeddings):
        results = evaluator.evaluate_cosine(query, response, sample_query_result)
        
        assert isinstance(results, dict)
        assert all(metric in results for metric in ['relevance', 'coherence', 'faithfulness', 'overall_score'])
        assert all(isinstance(score, float) for score in results.values())
        assert 0 <= results['overall_score'] <= 1

def test_calculate_relevance_score(evaluator, sample_query_result):
    """Test the _calculate_relevance_score method."""
    query = "What is relativity?"
    
    # Mock embeddings for consistent testing
    query_embedding = np.array([[1.0, 0.0]])
    doc_embeddings = np.array([[0.9, 0.1], [0.8, 0.2], [0.7, 0.3]])
    
    with patch('rag_solution.evaluation.evaluator.get_embeddings') as mock_get_embeddings:
        mock_get_embeddings.side_effect = [query_embedding, doc_embeddings]
        
        score = evaluator._calculate_relevance_score(query, sample_query_result)
        
        assert isinstance(score, float)
        assert 0 <= score <= 1

def test_calculate_coherence_score(evaluator):
    """Test the _calculate_coherence_score method."""
    query = "What is relativity?"
    response = "Relativity describes the relationship between space and time."
    
    # Mock embeddings for consistent testing
    query_embedding = np.array([[1.0, 0.0]])
    response_embedding = np.array([[0.9, 0.1]])
    
    with patch('rag_solution.evaluation.evaluator.get_embeddings') as mock_get_embeddings:
        mock_get_embeddings.side_effect = [query_embedding, response_embedding]
        
        score = evaluator._calculate_coherence_score(query, response)
        
        assert isinstance(score, float)
        assert 0 <= score <= 1

def test_calculate_faithfulness_score(evaluator, sample_query_result):
    """Test the _calculate_faithfulness_score method."""
    response = "The theory of relativity explains gravity and spacetime."
    
    # Mock embeddings for consistent testing
    response_embedding = np.array([[1.0, 0.0]])
    doc_embeddings = np.array([[0.9, 0.1], [0.8, 0.2], [0.7, 0.3]])
    
    with patch('rag_solution.evaluation.evaluator.get_embeddings') as mock_get_embeddings:
        mock_get_embeddings.side_effect = [response_embedding, doc_embeddings]
        
        score = evaluator._calculate_faithfulness_score(response, sample_query_result)
        
        assert isinstance(score, float)
        assert 0 <= score <= 1

@pytest.mark.asyncio
async def test_evaluate_async(evaluator):
    """Test the async evaluate method."""
    context = "Einstein developed the theory of relativity."
    answer = "The theory describes space, time, and gravity."
    question = "What is relativity?"
    
    # Mock LLM and evaluators
    mock_llm = AsyncMock()
    mock_llm.aclose_persistent_connection = AsyncMock()
    
    with patch('rag_solution.evaluation.evaluator.init_llm', return_value=mock_llm), \
         patch.object(evaluator.faithfulness_evaluator, 'a_evaluate', return_value=0.8), \
         patch.object(evaluator.answer_relevance_evaluator, 'a_evaluate', return_value=0.9), \
         patch.object(evaluator.context_relevance_evaluator, 'a_evaluate', return_value=0.7):
        
        results = await evaluator.evaluate(context, answer, question)
        
        assert isinstance(results, dict)
        assert all(metric in results for metric in ['faithfulness', 'answer_relevance', 'context_relevance'])
        assert all(isinstance(score, float) for score in results.values())
        assert mock_llm.aclose_persistent_connection.called

@pytest.mark.asyncio
async def test_evaluate_async_error_handling(evaluator):
    """Test error handling in the async evaluate method."""
    context = "Test context"
    answer = "Test answer"
    question = "Test question"
    
    # Mock LLM to raise an exception
    mock_llm = AsyncMock()
    mock_llm.aclose_persistent_connection = AsyncMock()
    
    with patch('rag_solution.evaluation.evaluator.init_llm', return_value=mock_llm), \
         patch.object(evaluator.faithfulness_evaluator, 'a_evaluate', side_effect=Exception("Test error")):
        
        with pytest.raises(RuntimeError):
            await evaluator.evaluate(context, answer, question)
        
        assert mock_llm.aclose_persistent_connection.called

def test_edge_cases(evaluator):
    """Test edge cases and error handling."""
    # Empty query and response
    with patch('rag_solution.evaluation.evaluator.get_embeddings', return_value=np.array([[0.0, 0.0]])):
        results = evaluator.evaluate_cosine("", "", [])
        assert all(score == 0.0 for score in results.values())
    
    # Single document
    single_doc = [QueryResult(data=[DocumentChunk(chunk_id='1', text="Test", score=1.0)])]
    with patch('rag_solution.evaluation.evaluator.get_embeddings', return_value=np.array([[1.0, 0.0]])):
        results = evaluator.evaluate_cosine("test", "test", single_doc)
        assert all(isinstance(score, float) for score in results.values())
    
    # Long text handling
    long_text = "Long " * 1000
    with patch('rag_solution.evaluation.evaluator.get_embeddings', return_value=np.array([[1.0, 0.0]])):
        score = evaluator._calculate_coherence_score(long_text, long_text)
        assert isinstance(score, float)

def test_numerical_stability(evaluator):
    """Test numerical stability with various input patterns."""
    # Test with very similar vectors
    similar_embeddings = np.array([[1.0, 0.0], [0.99999, 0.00001]])
    with patch('rag_solution.evaluation.evaluator.get_embeddings', return_value=similar_embeddings):
        score = evaluator._calculate_coherence_score("test", "test")
        assert 0 <= score <= 1
    
    # Test with very different vectors
    different_embeddings = np.array([[1.0, 0.0], [-1.0, 0.0]])
    with patch('rag_solution.evaluation.evaluator.get_embeddings', return_value=different_embeddings):
        score = evaluator._calculate_coherence_score("test", "completely different")
        assert 0 <= score <= 1
    
    # Test with zero vectors
    zero_embeddings = np.array([[0.0, 0.0], [0.0, 0.0]])
    with patch('rag_solution.evaluation.evaluator.get_embeddings', return_value=zero_embeddings):
        score = evaluator._calculate_coherence_score("zero", "zero")
        assert 0 <= score <= 1

if __name__ == "__main__":
    pytest.main([__file__])
