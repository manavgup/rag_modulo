import pytest
from unittest.mock import MagicMock, patch
from rag_solution.retrieval.retriever import VectorRetriever, KeywordRetriever, HybridRetriever
from vectordbs.data_types import Document, QueryResult

@pytest.fixture
def mock_vector_store():
    return MagicMock()

@pytest.fixture
def sample_documents():
    return [
        Document(id="1", content="Einstein developed the theory of relativity."),
        Document(id="2", content="Newton discovered the laws of motion and universal gravitation."),
        Document(id="3", content="Quantum mechanics describes the behavior of matter and energy at the atomic scale.")
    ]

@pytest.fixture
def mock_get_embeddings():
    return MagicMock(return_value=[[0.1, 0.2, 0.3]])

def test_vector_retriever_init(mock_vector_store):
    retriever = VectorRetriever(mock_vector_store)
    assert retriever.vector_store == mock_vector_store

@patch('rag_solution.retrieval.retriever.get_embeddings')
def test_vector_retriever_retrieve(mock_get_embeddings, mock_vector_store):
    mock_get_embeddings.return_value = [[0.1, 0.2, 0.3]]
    mock_vector_store.query.return_value = [
        QueryResult(document=Document(id="1", content="Test content"), score=0.9)
    ]

    retriever = VectorRetriever(mock_vector_store)
    results = retriever.retrieve("test query", k=1)

    assert len(results) == 1
    assert results[0].document.id == "1"
    assert results[0].score == 0.9
    mock_get_embeddings.assert_called_once_with(["test query"])
    mock_vector_store.query.assert_called_once()

def test_keyword_retriever_init(sample_documents):
    retriever = KeywordRetriever(sample_documents)
    assert len(retriever.documents) == 3

def test_keyword_retriever_retrieve(sample_documents):
    retriever = KeywordRetriever(sample_documents)
    results = retriever.retrieve("theory of relativity", k=2)

    assert len(results) == 2
    assert results[0].document.id == "1"
    assert results[0].score > results[1].score

def test_hybrid_retriever_init(mock_vector_store, sample_documents):
    retriever = HybridRetriever(mock_vector_store, sample_documents, vector_weight=0.7)
    assert isinstance(retriever.vector_retriever, VectorRetriever)
    assert isinstance(retriever.keyword_retriever, KeywordRetriever)
    assert retriever.vector_weight == 0.7

@patch('rag_solution.retrieval.retriever.VectorRetriever.retrieve')
@patch('rag_solution.retrieval.retriever.KeywordRetriever.retrieve')
def test_hybrid_retriever_retrieve(mock_vector_retrieve, mock_keyword_retrieve, mock_vector_store, sample_documents):
    mock_vector_retrieve.return_value = [
        QueryResult(document=Document(id="1", content="Vector content"), score=0.9)
    ]
    mock_keyword_retrieve.return_value = [
        QueryResult(document=Document(id="2", content="Keyword content"), score=0.8)
    ]

    retriever = HybridRetriever(mock_vector_store, sample_documents, vector_weight=0.7)
    results = retriever.retrieve("test query", k=2)

    assert len(results) == 2
    assert results[0].document.id == "1"
    assert results[1].document.id == "2"
    assert results[0].score > results[1].score

    mock_vector_retrieve.assert_called_once_with("test query", k=2)
    mock_keyword_retrieve.assert_called_once_with("test query", k=2)

if __name__ == "__main__":
    pytest.main()