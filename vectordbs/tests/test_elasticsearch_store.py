import pytest
from datetime import datetime
from elasticsearch.exceptions import NotFoundError
from vectordbs.elasticsearch_store import ElasticSearchStore
from vectordbs.data_types import (
    Document, DocumentChunk, DocumentChunkMetadata, Source, QueryWithEmbedding
)
from vectordbs.utils.watsonx import get_embeddings


ELASTICSEARCH_INDEX = "test_index"
def create_test_documents():
    text1 = "Hello world"
    text2 = "Hello Jello"
    text3 = "Tic Tac Toe"
    return [
        Document(document_id="doc1", name="Doc 1", chunks=[
            DocumentChunk(chunk_id="1", text=text1, vectors=get_embeddings(text1),
                          metadata=DocumentChunkMetadata(source=Source.WEBSITE,
                                                         created_at=datetime.now().isoformat() + 'Z'
                          ))
        ]),
        Document(document_id="doc2", name="Doc 2", chunks=[
            DocumentChunk(chunk_id="2", text=text2, vectors=get_embeddings(text2),
                          metadata=DocumentChunkMetadata(source=Source.WEBSITE,
                                                         created_at=datetime.now().isoformat() + 'Z'
                          ))
        ]),
        Document(document_id="doc3", name="Doc 3", chunks=[
            DocumentChunk(chunk_id="3", text=text3, vectors=get_embeddings(text3),
                          metadata=DocumentChunkMetadata(source=Source.WEBSITE,
                                                         created_at=datetime.now().isoformat() + 'Z'
                          ))
        ])
    ]

@pytest.fixture
def elasticsearch_store():
    store = ElasticSearchStore()
    store.create_collection(ELASTICSEARCH_INDEX, "sentence-transformers/all-minilm-l6-v2")
    yield store
    store.delete_collection(ELASTICSEARCH_INDEX)

def test_create_collection(elasticsearch_store):
    elasticsearch_store.create_collection("new_test_index", "sentence-transformers/all-minilm-l6-v2")
    assert elasticsearch_store.client.indices.exists(index="new_test_index")
    elasticsearch_store.delete_collection("new_test_index")

def test_add_documents(elasticsearch_store):
    documents = create_test_documents()
    result = elasticsearch_store.add_documents(ELASTICSEARCH_INDEX, documents)
    assert len(result) == 3
    assert result[0] == "1"

@pytest.mark.asyncio
async def test_query_documents(elasticsearch_store):
    documents = create_test_documents()
    elasticsearch_store.add_documents(ELASTICSEARCH_INDEX, documents)
    
    embeddings = get_embeddings("Hello world")
    
    query_results = elasticsearch_store.query(
        ELASTICSEARCH_INDEX, 
        QueryWithEmbedding(text="Hello world", vectors=embeddings)
    )
    assert query_results is not None
    assert len(query_results) > 0
    for query_result in query_results:
        assert query_result.data is not None
        assert len(query_result.data) > 0  

@pytest.mark.asyncio
async def test_retrieve_documents_with_string_query(elasticsearch_store):
    documents = create_test_documents()
    result = elasticsearch_store.add_documents(ELASTICSEARCH_INDEX, documents)
    assert len(result) == 3
    query_results = elasticsearch_store.retrieve_documents("Hello world", ELASTICSEARCH_INDEX)
    assert query_results is not None
    assert len(query_results) > 0
    
    for query_result in query_results:
        assert query_result.data is not None
        assert len(query_result.data) > 0  

@pytest.mark.asyncio
async def test_retrieve_documents_with_query_embedding(elasticsearch_store):
    documents = create_test_documents()
    result = elasticsearch_store.add_documents(ELASTICSEARCH_INDEX, documents)
    assert len(result) == 3

    query_embedding = QueryWithEmbedding(text="Hello world", vectors=get_embeddings("Hello world"))
    query_results = elasticsearch_store.retrieve_documents(query_embedding, ELASTICSEARCH_INDEX)

    assert query_results is not None
    assert len(query_results) > 0
    
    for query_result in query_results:
        assert query_result.data is not None
        assert len(query_result.data) > 0

def test_get_document(elasticsearch_store):
    documents = create_test_documents()
    elasticsearch_store.add_documents(ELASTICSEARCH_INDEX, documents)
    document = elasticsearch_store.get_document("doc1", ELASTICSEARCH_INDEX)
    assert document is not None
    assert document.document_id == "doc1"

@pytest.mark.asyncio
async def test_delete_documents_by_id(elasticsearch_store):
    documents = create_test_documents()
    elasticsearch_store.add_documents(ELASTICSEARCH_INDEX, documents)
    result = elasticsearch_store.delete_documents(['1'], ELASTICSEARCH_INDEX)
    assert result == 1
    query_result = elasticsearch_store.query(
        ELASTICSEARCH_INDEX, 
        QueryWithEmbedding(text="Hello world", vectors=get_embeddings("Hello world"))
    )
    assert len(query_result[0].data) == 0

@pytest.mark.asyncio
async def test_delete_all_documents(elasticsearch_store):
    documents = create_test_documents()
    elasticsearch_store.add_documents(ELASTICSEARCH_INDEX, documents)
    elasticsearch_store.delete_collection(ELASTICSEARCH_INDEX)
    # Attempting to query the deleted collection should raise an exception
    with pytest.raises(NotFoundError) as excinfo:
        elasticsearch_store.query(
            ELASTICSEARCH_INDEX, 
            QueryWithEmbedding(text="Hello world", vectors=get_embeddings("Hello world"))
        )
    assert "index_not_found_exception" in str(excinfo.value)
