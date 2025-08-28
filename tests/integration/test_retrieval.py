"""Tests for Retrieval Components."""

import pytest
from unittest.mock import Mock
from sqlalchemy.orm import Session

from rag_solution.retrieval.factories import RetrieverFactory
from rag_solution.retrieval.retriever import BaseRetriever, VectorRetriever, KeywordRetriever, HybridRetriever
from vectordbs.data_types import VectorQuery


@pytest.fixture
def document_store():
    """Create a mock document store."""
    store = Mock()
    store.vector_store = Mock()
    store.get_documents = Mock(return_value=[])
    return store

class TestRetrievers:
    def test_vector_retriever_success(self, document_store):
        """Test successful vector retrieval."""
        retriever = VectorRetriever(document_store)
        query = VectorQuery(text="test query", number_of_results=5)
        
        # Mock vector store response
        document_store.vector_store.retrieve_documents.return_value = []
        
        result = retriever.retrieve("test_collection", query)
        assert isinstance(result, list)
        assert document_store.vector_store.retrieve_documents.called

    def test_vector_retriever_error(self, document_store):
        """Test vector retrieval error handling."""
        retriever = VectorRetriever(document_store)
        query = VectorQuery(text="test query", number_of_results=5)
        
        # Mock vector store error
        document_store.vector_store.retrieve_documents.side_effect = ValueError("Vector store error")
        
        result = retriever.retrieve("test_collection", query)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_keyword_retriever_success(self, document_store):
        """Test successful keyword retrieval."""
        retriever = KeywordRetriever(document_store)
        query = VectorQuery(text="test query", number_of_results=5)
        
        result = retriever.retrieve("test_collection", query)
        assert isinstance(result, list)
        assert document_store.get_documents.called

    def test_keyword_retriever_error(self, document_store):
        """Test keyword retrieval error handling."""
        retriever = KeywordRetriever(document_store)
        query = VectorQuery(text="test query", number_of_results=5)
        
        # Mock document store error
        document_store.get_documents.side_effect = Exception("Document store error")
        
        result = retriever.retrieve("test_collection", query)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_hybrid_retriever_success(self, document_store):
        """Test successful hybrid retrieval."""
        retriever = HybridRetriever(document_store)
        query = VectorQuery(text="test query", number_of_results=5)
        
        result = retriever.retrieve("test_collection", query)
        assert isinstance(result, list)
        assert document_store.vector_store.retrieve_documents.called
        assert document_store.get_documents.called

    def test_hybrid_retriever_partial_failure(self, document_store):
        """Test hybrid retrieval with partial failure."""
        retriever = HybridRetriever(document_store)
        query = VectorQuery(text="test query", number_of_results=5)
        
        # Mock vector store error but keyword success
        document_store.vector_store.retrieve_documents.side_effect = ValueError("Vector store error")
        document_store.get_documents.return_value = []
        
        result = retriever.retrieve("test_collection", query)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_hybrid_retriever_custom_weight(self, document_store):
        """Test hybrid retrieval with custom vector weight."""
        retriever = HybridRetriever(document_store, vector_weight=0.3)
        query = VectorQuery(text="test query", number_of_results=5)
        
        result = retriever.retrieve("test_collection", query)
        assert isinstance(result, list)
        assert retriever.vector_weight == 0.3

class TestRetrieverFactory:
    def test_vector_retriever_creation(self, document_store):
        """Test vector retriever creation."""
        vector_config = {'type': 'vector'}
        vector_retriever = RetrieverFactory.create_retriever(vector_config, document_store)
        assert isinstance(vector_retriever, VectorRetriever)
    
    def test_keyword_retriever_creation(self, document_store):
        """Test keyword retriever creation."""
        keyword_config = {'type': 'keyword'}
        keyword_retriever = RetrieverFactory.create_retriever(keyword_config, document_store)
        assert isinstance(keyword_retriever, KeywordRetriever)
    
    def test_hybrid_retriever_creation(self, document_store):
        """Test hybrid retriever creation."""
        hybrid_config = {'type': 'hybrid', 'vector_weight': 0.7}
        hybrid_retriever = RetrieverFactory.create_retriever(hybrid_config, document_store)
        assert isinstance(hybrid_retriever, HybridRetriever)
    
    def test_default_retriever_type(self, document_store):
        """Test default retriever type (vector)."""
        config = {}  # No type specified
        retriever = RetrieverFactory.create_retriever(config, document_store)
        assert isinstance(retriever, VectorRetriever)
    
    def test_invalid_retriever_type(self, document_store):
        """Test invalid retriever type."""
        config = {'type': 'invalid'}
        with pytest.raises(ValueError, match="Invalid retriever type: invalid"):
            RetrieverFactory.create_retriever(config, document_store)
    
    def test_hybrid_retriever_custom_weight(self, document_store):
        """Test hybrid retriever with custom vector weight."""
        config = {'type': 'hybrid', 'vector_weight': 0.3}
        retriever = RetrieverFactory.create_retriever(config, document_store)
        assert isinstance(retriever, HybridRetriever)
        assert retriever.vector_weight == 0.3

if __name__ == "__main__":
    pytest.main([__file__])
