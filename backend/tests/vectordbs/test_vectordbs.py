"""Tests for Vector Database Components."""

from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from vectordbs.chroma_store import ChromaDBStore
from vectordbs.data_types import DocumentChunk
from vectordbs.elasticsearch_store import ElasticSearchStore
from vectordbs.factory import get_datastore
from vectordbs.milvus_store import MilvusStore
from vectordbs.pinecone_store import PineconeStore
from vectordbs.utils.watsonx import get_embeddings
from vectordbs.weaviate_store import WeaviateDataStore


@pytest.fixture
def mock_vectordb_session():
    """Create a mock database session with context manager support."""
    mock_session = Mock()

    # Mock the context manager protocol
    mock_session.begin_nested.return_value.__enter__.return_value = mock_session
    mock_session.begin_nested.return_value.__exit__.return_value = None

    # Mock commit and rollback
    mock_session.commit.return_value = None
    mock_session.rollback.return_value = None

    return mock_session


def test_vector_db_factory():
    """Test the VectorDBFactory."""
    # Test creating Pinecone store
    pinecone_store = get_datastore("pinecone")
    assert isinstance(pinecone_store, PineconeStore)

    # Test creating Weaviate store
    weaviate_store = get_datastore("weaviate")
    assert isinstance(weaviate_store, WeaviateDataStore)

    # Test creating Milvus store
    milvus_store = get_datastore("milvus")
    assert isinstance(milvus_store, MilvusStore)

    # Test creating Elasticsearch store
    es_store = get_datastore("elasticsearch")
    assert isinstance(es_store, ElasticSearchStore)


@patch("vectordbs.utils.watsonx.get_embeddings")
def test_chroma_vector_store(mock_get_embeddings, mock_vectordb_session):
    """Test the ChromaDBStore."""
    mock_get_embeddings.return_value = [0.1, 0.2, 0.3]
    store = ChromaDBStore(mock_vectordb_session)

    # Test adding and retrieving vector data
    test_text = "test text"
    embeddings = get_embeddings(test_text)
    vector_data = DocumentChunk(chunk_id=uuid4(), text=test_text, embeddings=embeddings, metadata={"text": test_text})
    store.add_vector(vector_data)
    retrieved = store.get_vector(vector_data.chunk_id)
    assert retrieved == vector_data


@patch("vectordbs.utils.watsonx.get_embeddings")
def test_elasticsearch_vector_store(mock_get_embeddings, mock_vectordb_session):
    """Test the ElasticSearchStore."""
    mock_get_embeddings.return_value = [0.1, 0.2, 0.3]
    store = ElasticSearchStore(mock_vectordb_session)

    # Test adding and retrieving vector data
    test_text = "test text"
    embeddings = get_embeddings(test_text)
    vector_data = DocumentChunk(chunk_id=uuid4(), text=test_text, embeddings=embeddings, metadata={"text": test_text})
    store.add_vector(vector_data)
    retrieved = store.get_vector(vector_data.chunk_id)
    assert retrieved == vector_data


@patch("vectordbs.utils.watsonx.get_embeddings")
def test_milvus_vector_store(mock_get_embeddings, mock_vectordb_session):
    """Test the MilvusStore."""
    mock_get_embeddings.return_value = [0.1, 0.2, 0.3]
    store = MilvusStore(mock_vectordb_session)

    # Test adding and retrieving vector data
    test_text = "test text"
    embeddings = get_embeddings(test_text)
    vector_data = DocumentChunk(chunk_id=uuid4(), text=test_text, embeddings=embeddings, metadata={"text": test_text})
    store.add_vector(vector_data)
    retrieved = store.get_vector(vector_data.chunk_id)
    assert retrieved == vector_data


@patch("vectordbs.utils.watsonx.get_embeddings")
def test_pinecone_vector_store(mock_get_embeddings, mock_vectordb_session):
    """Test the PineconeStore."""
    mock_get_embeddings.return_value = [0.1, 0.2, 0.3]
    store = PineconeStore(mock_vectordb_session)

    # Test adding and retrieving vector data
    test_text = "test text"
    embeddings = get_embeddings(test_text)
    vector_data = DocumentChunk(chunk_id=uuid4(), text=test_text, embeddings=embeddings, metadata={"text": test_text})
    store.add_vector(vector_data)
    retrieved = store.get_vector(vector_data.chunk_id)
    assert retrieved == vector_data


@patch("vectordbs.utils.watsonx.get_embeddings")
def test_weaviate_vector_store(mock_get_embeddings, mock_vectordb_session):
    """Test the WeaviateDataStore."""
    mock_get_embeddings.return_value = [0.1, 0.2, 0.3]
    store = WeaviateDataStore(mock_vectordb_session)

    # Test adding and retrieving vector data
    test_text = "test text"
    embeddings = get_embeddings(test_text)
    vector_data = DocumentChunk(chunk_id=uuid4(), text=test_text, embeddings=embeddings, metadata={"text": test_text})
    store.add_vector(vector_data)
    retrieved = store.get_vector(vector_data.chunk_id)
    assert retrieved == vector_data


if __name__ == "__main__":
    pytest.main([__file__])
