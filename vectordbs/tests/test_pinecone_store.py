from datetime import datetime

import pytest

from vectordbs.data_types import (Document, DocumentChunk,
                                  DocumentChunkMetadata,
                                  DocumentMetadataFilter, QueryWithEmbedding,
                                  Source)
from vectordbs.pinecone_store import PineconeStore
from vectordbs.utils.watsonx import get_embeddings

PINECONE_INDEX = "test-index"


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
def pinecone_store():
    store = PineconeStore()
    store.create_collection(PINECONE_INDEX, "sentence-transformers/all-minilm-l6-v2")
    try:
        yield store
    finally:
        store.delete_collection(PINECONE_INDEX)


def test_create_collection(pinecone_store):
    pinecone_store.create_collection(
        "new-test-index", "sentence-transformers/all-minilm-l6-v2"
    )
    index = pinecone_store.index
    assert index is not None
    pinecone_store.delete_collection("new-test-index")


def test_add_documents(pinecone_store):
    documents = create_test_documents()
    result = pinecone_store.add_documents(PINECONE_INDEX, documents)
    assert len(result) == 3
    assert result[0] == "1"


def test_query_documents(pinecone_store):
    documents = create_test_documents()
    pinecone_store.add_documents(PINECONE_INDEX, documents)

    embeddings = get_embeddings("Hello world")

    query_results = pinecone_store.retrieve_documents(
        QueryWithEmbedding(text="Hello world", vectors=embeddings),
        PINECONE_INDEX,
        limit=10,
    )
    assert query_results is not None
    assert len(query_results) > 0
    for query_result in query_results:
        assert query_result.data is not None
        assert len(query_result.data) > 0


def test_retrieve_documents_with_string_query(pinecone_store):
    documents = create_test_documents()
    result = pinecone_store.add_documents(PINECONE_INDEX, documents)
    assert len(result) == 3
    query_results = pinecone_store.retrieve_documents(
        "Hello world", PINECONE_INDEX, limit=10
    )
    assert query_results is not None
    assert len(query_results) > 0

    for query_result in query_results:
        assert query_result.data is not None
        assert len(query_result.data) > 0


def test_delete_documents(pinecone_store):
    documents = create_test_documents()
    added_ids = pinecone_store.add_documents(PINECONE_INDEX, documents)

    # Delete empty list
    deleted_count = pinecone_store.delete_documents([], PINECONE_INDEX)
    assert deleted_count == 0

    # Delete one document and verify
    chunk_id_to_delete = added_ids[0]
    deleted_count = pinecone_store.delete_documents(
        [chunk_id_to_delete], PINECONE_INDEX
    )
    assert deleted_count == 1

    # Remove the deleted document from the list of added IDs for the next test
    added_ids.remove(chunk_id_to_delete)

    # Delete non-existent document
    deleted_count = pinecone_store.delete_documents(["non_existent_id"], PINECONE_INDEX)
    assert deleted_count == 1  # Assuming deletion attempt on all ids passed

    # Delete all remaining documents
    deleted_count = pinecone_store.delete_documents(added_ids, PINECONE_INDEX)
    assert deleted_count == len(added_ids)  # Check if all remaining were deleted

    delete_from_wrong_index = pinecone_store.delete_documents(added_ids, "wrong_index")
    assert delete_from_wrong_index == 0


def test_delete_all_documents(pinecone_store):
    documents = create_test_documents()
    pinecone_store.add_documents(PINECONE_INDEX, documents)
    pinecone_store.delete_collection(PINECONE_INDEX)
    # Attempting to query the deleted collection should raise an exception
    with pytest.raises(Exception):
        pinecone_store.retrieve_documents(
            QueryWithEmbedding(
                text="Hello world", vectors=get_embeddings("Hello world")
            ),
            PINECONE_INDEX,
            limit=10,
        )


def test_convert_to_chunk():
    store = PineconeStore()
    sample_data = {
        "id": "1",
        "values": [0.1] * 384,
        "metadata": {
            "text": "Sample text",
            "document_id": "doc1",
            "source": "website",
            "source_id": "source_1",
            "url": "http://example.com",
            "created_at": "2023-01-01T00:00:00Z",
            "author": "Author Name",
        },
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
    store = PineconeStore()
    sample_response = {
        "matches": [
            {
                "score": 1.0,
                "id": "1",
                "values": [0.1] * 384,
                "metadata": {
                    "text": "Sample text",
                    "document_id": "doc1",
                    "source": "website",
                    "source_id": "source_1",
                    "url": "http://example.com",
                    "created_at": "2023-01-01T00:00:00Z",
                    "author": "Author Name",
                },
            }
        ]
    }
    results = store._process_search_results(sample_response)
    assert len(results) == 1
    assert results[0].data[0].chunk_id == "1"
    assert results[0].data[0].text == "Sample text"


def test_build_filters():
    store = PineconeStore()
    filter_eq = DocumentMetadataFilter(
        field_name="author", value="John Doe", operator="eq"
    )
    with pytest.raises(NotImplementedError):
        store._build_filters(filter_eq)


@pytest.mark.asyncio
async def test_aenter_aexit():
    async with PineconeStore() as store:
        assert isinstance(store, PineconeStore)
    # Ensure the store is closed after exiting the context manager
