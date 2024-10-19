import pytest
from backend.rag_solution.evaluation.evaluator import RAGEvaluator, AnswerQuality, HallucinationSeverity, AnswerCompleteness, ContextRelevancy, QuestionAmbiguity

@pytest.fixture
def evaluator():
    return RAGEvaluator()

@pytest.fixture
def sample_query():
    return "What is the capital of France?"

@pytest.fixture
def sample_response():
    return "The capital of France is Paris. It is known for its iconic landmarks such as the Eiffel Tower and the Louvre Museum."

@pytest.fixture
def sample_documents():
    return [
        {"content": "Paris is the capital and most populous city of France.", "id": "doc1"},
        {"content": "France is a country in Western Europe with many famous landmarks.", "id": "doc2"},
        {"content": "The Eiffel Tower is located in Paris and is one of the most recognizable structures in the world.", "id": "doc3"}
    ]

def test_evaluate_relevance(evaluator, sample_query, sample_response, sample_documents):
    relevance = evaluator.evaluate_relevance(sample_query, sample_response, sample_documents)
    assert 0 <= relevance <= 1

def test_evaluate_coherence(evaluator, sample_response):
    coherence = evaluator.evaluate_coherence(sample_response)
    assert 0 <= coherence <= 1

def test_evaluate_factual_accuracy(evaluator, sample_response, sample_documents):
    factual_accuracy = evaluator.evaluate_factual_accuracy(sample_response, sample_documents)
    assert 0 <= factual_accuracy <= 1

def test_calculate_hit_rate(evaluator):
    relevant_docs = ["doc1", "doc3"]
    retrieved_docs = ["doc1", "doc2", "doc3"]
    hit_rate = evaluator.calculate_hit_rate(relevant_docs, retrieved_docs)
    assert hit_rate == 1.0

def test_calculate_mrr(evaluator):
    relevant_docs = ["doc1", "doc3"]
    retrieved_docs = ["doc1", "doc2", "doc3"]
    mrr = evaluator.calculate_mrr(relevant_docs, retrieved_docs)
    assert mrr == 1.0

def test_calculate_ndcg(evaluator):
    relevant_docs = ["doc1", "doc3"]
    retrieved_docs = ["doc1", "doc2", "doc3"]
    ndcg = evaluator.calculate_ndcg(relevant_docs, retrieved_docs)
    assert 0 <= ndcg <= 1

def test_calculate_precision_at_k(evaluator):
    relevant_docs = ["doc1", "doc3"]
    retrieved_docs = ["doc1", "doc2", "doc3"]
    precision = evaluator.calculate_precision_at_k(relevant_docs, retrieved_docs, k=2)
    assert precision == 0.5

def test_evaluate_answer_quality(evaluator, sample_response, sample_documents):
    result = evaluator.evaluate_answer_quality(sample_response, sample_documents)
    assert isinstance(result, AnswerQuality)

def test_evaluate_hallucination(evaluator, sample_response, sample_documents):
    result = evaluator.evaluate_hallucination(sample_response, sample_documents)
    assert isinstance(result, HallucinationSeverity)

def test_evaluate_answer_completeness(evaluator, sample_query, sample_response, sample_documents):
    result = evaluator.evaluate_answer_completeness(sample_query, sample_response, sample_documents)
    assert isinstance(result, AnswerCompleteness)

def test_evaluate_context_relevancy(evaluator, sample_query, sample_documents):
    result = evaluator.evaluate_context_relevancy(sample_query, sample_documents)
    assert isinstance(result, ContextRelevancy)

def test_evaluate_question_ambiguity(evaluator, sample_query):
    result = evaluator.evaluate_question_ambiguity(sample_query)
    assert isinstance(result, QuestionAmbiguity)

def test_evaluate(evaluator, sample_query, sample_response, sample_documents):
    relevant_docs = ["doc1", "doc3"]
    result = evaluator.evaluate(sample_query, sample_response, sample_documents, relevant_docs)
    assert isinstance(result, dict)
    assert "relevance" in result
    assert "coherence" in result
    assert "factual_accuracy" in result
    assert "answer_quality" in result
    assert "hallucination" in result
    assert "answer_completeness" in result
    assert "context_relevancy" in result
    assert "question_ambiguity" in result
    assert "hit_rate" in result
    assert "mrr" in result
    assert "ndcg" in result
    assert "precision_at_3" in result
    assert "precision_at_5" in result