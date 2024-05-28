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

@pytest.mark.asyncio  # For async test
async def test_delete_documents(elasticsearch_store):
    documents = create_test_documents()
    added_ids = elasticsearch_store.add_documents(ELASTICSEARCH_INDEX, documents)

    # Delete empty list
    deleted_count = elasticsearch_store.delete_documents([], ELASTICSEARCH_INDEX)
    assert deleted_count == 0

    # Delete one document and verify
    chunk_id_to_delete = added_ids[0]
    deleted_count = elasticsearch_store.delete_documents([chunk_id_to_delete], ELASTICSEARCH_INDEX)
    assert deleted_count == 1

    # Ensure the deleted document is no longer retrievable
    with pytest.raises(NotFoundError):
        elasticsearch_store.client.get(index=ELASTICSEARCH_INDEX, id=chunk_id_to_delete)

    # Remove the deleted document from the list of added IDs for the next test
    added_ids.remove(chunk_id_to_delete)

    # Delete non-existent document
    deleted_count = elasticsearch_store.delete_documents(["non_existent_id"], ELASTICSEARCH_INDEX)
    assert deleted_count == 0
 
    # Delete all remaining documents
    deleted_count = elasticsearch_store.delete_documents(added_ids, ELASTICSEARCH_INDEX)
    assert deleted_count == len(added_ids)  # Check if all remaining were deleted

    delete_from_wrong_index = elasticsearch_store.delete_documents(added_ids, "wrong_index") 
    assert delete_from_wrong_index == 0

    # Ensure that the index is now empty.
    response = elasticsearch_store.client.count(index=ELASTICSEARCH_INDEX)
    assert response['count'] == 0

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
