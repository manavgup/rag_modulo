from datetime import datetime

import pytest
from elasticsearch.exceptions import NotFoundError

from vectordbs.data_types import (Document, DocumentChunk,
                                  DocumentChunkMetadata,
                                  DocumentMetadataFilter, QueryWithEmbedding,
                                  Source)
from vectordbs.elasticsearch_store import ElasticSearchStore
from vectordbs.utils.watsonx import get_embeddings

ELASTICSEARCH_INDEX = "test_index"


def create_test_documents():
    text1 = "Hello world"
    text2 = "Hello Jello"
    text3 = "Tic Tac Toe"
    return [
        Document(
            document_id="doc1",
            name="Doc 1",
            chunks=[
                DocumentChunk(
                    chunk_id="1",
                    text=text1,
                    vectors=get_embeddings(text1),
                    metadata=DocumentChunkMetadata(
                        source=Source.WEBSITE,
                        created_at=datetime.now().isoformat() + "Z",
                    ),
                )
            ],
        ),
        Document(
            document_id="doc2",
            name="Doc 2",
            chunks=[
                DocumentChunk(
                    chunk_id="2",
                    text=text2,
                    vectors=get_embeddings(text2),
                    metadata=DocumentChunkMetadata(
                        source=Source.WEBSITE,
                        created_at=datetime.now().isoformat() + "Z",
                    ),
                )
            ],
        ),
        Document(
            document_id="doc3",
            name="Doc 3",
            chunks=[
                DocumentChunk(
                    chunk_id="3",
                    text=text3,
                    vectors=get_embeddings(text3),
                    metadata=DocumentChunkMetadata(
                        source=Source.WEBSITE,
                        created_at=datetime.now().isoformat() + "Z",
                    ),
                )
            ],
        ),
    ]


@pytest.fixture
def elasticsearch_store():
    store = ElasticSearchStore()
    store.create_collection(
        ELASTICSEARCH_INDEX, "sentence-transformers/all-minilm-l6-v2"
    )
    yield store
    store.delete_collection(ELASTICSEARCH_INDEX)


def test_create_collection(elasticsearch_store):
    elasticsearch_store.create_collection(
        "new_test_index", "sentence-transformers/all-minilm-l6-v2"
    )
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
        ELASTICSEARCH_INDEX, QueryWithEmbedding(text="Hello world", vectors=embeddings)
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
    query_results = elasticsearch_store.retrieve_documents(
        "Hello world", ELASTICSEARCH_INDEX
    )
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

    query_embedding = QueryWithEmbedding(
        text="Hello world", vectors=get_embeddings("Hello world")
    )
    query_results = elasticsearch_store.retrieve_documents(
        query_embedding, ELASTICSEARCH_INDEX
    )

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
    deleted_count = elasticsearch_store.delete_documents(
        [chunk_id_to_delete], ELASTICSEARCH_INDEX
    )
    assert deleted_count == 1

    # Ensure the deleted document is no longer retrievable
    with pytest.raises(NotFoundError):
        elasticsearch_store.client.get(index=ELASTICSEARCH_INDEX, id=chunk_id_to_delete)

    # Remove the deleted document from the list of added IDs for the next test
    added_ids.remove(chunk_id_to_delete)

    # Delete non-existent document
    deleted_count = elasticsearch_store.delete_documents(
        ["non_existent_id"], ELASTICSEARCH_INDEX
    )
    assert deleted_count == 0

    # Delete all remaining documents
    deleted_count = elasticsearch_store.delete_documents(added_ids, ELASTICSEARCH_INDEX)
    assert deleted_count == len(added_ids)  # Check if all remaining were deleted

    delete_from_wrong_index = elasticsearch_store.delete_documents(
        added_ids, "wrong_index"
    )
    assert delete_from_wrong_index == 0

    # Ensure that the index is now empty.
    response = elasticsearch_store.client.count(index=ELASTICSEARCH_INDEX)
    assert response["count"] == 0


@pytest.mark.asyncio
async def test_delete_all_documents(elasticsearch_store):
    documents = create_test_documents()
    elasticsearch_store.add_documents(ELASTICSEARCH_INDEX, documents)
    elasticsearch_store.delete_collection(ELASTICSEARCH_INDEX)
    # Attempting to query the deleted collection should raise an exception
    with pytest.raises(NotFoundError) as excinfo:
        elasticsearch_store.query(
            ELASTICSEARCH_INDEX,
            QueryWithEmbedding(
                text="Hello world", vectors=get_embeddings("Hello world")
            ),
        )
    assert "index_not_found_exception" in str(excinfo.value)


# Add the following test cases to test_elasticsearch_store.py


def test_convert_to_chunk():
    store = ElasticSearchStore()
    sample_data = {
        "chunk_id": "1",
        "text": "Sample text",
        "embedding": [0.1] * 384,
        "source": "website",
        "source_id": "source_1",
        "url": "http://example.com",
        "created_at": "2023-01-01T00:00:00Z",
        "author": "Author Name",
        "document_id": "doc1",
    }
    chunk = store._convert_to_chunk(sample_data)
    assert chunk.chunk_id == "1"
    assert chunk.text == "Sample text"
    assert chunk.vectors == [0.1] * 384
    assert chunk.metadata.source == Source.WEBSITE
    assert chunk.metadata.source_id == "source_1"
    assert chunk.metadata.url == "http://example.com"
    assert chunk.metadata.created_at == "2023-01-01T00:00:00Z"
    assert chunk.metadata.author == "Author Name"
    assert chunk.document_id == "doc1"


def test_process_search_results():
    store = ElasticSearchStore()
    sample_response = {
        "hits": {
            "hits": [
                {
                    "_score": 1.0,
                    "_source": {
                        "chunk_id": "1",
                        "text": "Sample text",
                        "embedding": [0.1] * 384,
                        "source": "website",
                        "source_id": "source_1",
                        "url": "http://example.com",
                        "created_at": "2023-01-01T00:00:00Z",
                        "author": "Author Name",
                        "document_id": "doc1",
                    },
                }
            ]
        }
    }
    results = store._process_search_results(sample_response)
    assert len(results) == 1
    assert results[0].data[0].chunk_id == "1"
    assert results[0].data[0].text == "Sample text"


def test_build_filters():
    store = ElasticSearchStore()
    filter_eq = DocumentMetadataFilter(
        field_name="author", value="John Doe", operator="eq"
    )
    filter_gte = DocumentMetadataFilter(
        field_name="created_at", value="2023-01-01T00:00:00Z", operator="gte"
    )
    filter_lte = DocumentMetadataFilter(
        field_name="created_at", value="2023-12-31T23:59:59Z", operator="lte"
    )

    filters_eq = store._build_filters(filter_eq)
    filters_gte = store._build_filters(filter_gte)
    filters_lte = store._build_filters(filter_lte)

    assert filters_eq == {"bool": {"filter": [{"term": {"author": "John Doe"}}]}}
    assert filters_gte == {
        "bool": {"filter": [{"range": {"created_at": {"gte": "2023-01-01T00:00:00Z"}}}]}
    }
    assert filters_lte == {
        "bool": {"filter": [{"range": {"created_at": {"lte": "2023-12-31T23:59:59Z"}}}]}
    }


def test_add_documents_error_handling():
    store = ElasticSearchStore()
    documents = create_test_documents()

    # Try adding documents to a non-existent index
    with pytest.raises(Exception):
        store.add_documents("non_existent_index", documents)


def test_query_error_handling():
    store = ElasticSearchStore()
    embeddings = get_embeddings("Hello world")

    # Try querying a non-existent index
    with pytest.raises(Exception):
        store.query(
            "non_existent_index",
            QueryWithEmbedding(text="Hello world", vectors=embeddings),
        )


@pytest.mark.asyncio
async def test_aenter_aexit():
    async with ElasticSearchStore() as store:
        assert isinstance(store, ElasticSearchStore)
