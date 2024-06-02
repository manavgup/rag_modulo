import pytest
from datetime import datetime
from vectordbs.milvus_store import MilvusStore
from vectordbs.data_types import (
    Document,
    DocumentChunk,
    DocumentChunkMetadata,
    Source,
    QueryWithEmbedding,
)
import json
from vectordbs.utils.watsonx import get_embeddings
from pymilvus import MilvusException


@pytest.fixture
def milvus_store():
    store = MilvusStore()
    store.create_collection(
        "test_collection",
        embedding_model_id="sentence-transformers/all-minilm-l6-v2",
        client=store.client,
    )
    yield store
    store.delete_collection("test_collection")


def create_test_documents():
    return [
        Document(
            document_id="doc1",
            name="Doc 1",
            chunks=[
                DocumentChunk(
                    chunk_id="1",
                    text="Hello world",
                    vectors=get_embeddings("Hello world"),
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
                    chunk_id="1",
                    text="Hello Jello",
                    vectors=get_embeddings("Hello Jello"),
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
                    chunk_id="1",
                    text="Tic Tac Toe",
                    vectors=get_embeddings("Tic Tac Toe"),
                    metadata=DocumentChunkMetadata(
                        source=Source.WEBSITE,
                        created_at=datetime.now().isoformat() + "Z",
                    ),
                )
            ],
        ),
    ]


def test_create_collection(milvus_store):
    milvus_store.create_collection(
        "test_new_collection",
        embedding_model_id="sentence-transformers/all-minilm-l6-v2",
        client=milvus_store.client,
    )
    collection = milvus_store.collection
    assert collection is not None
    milvus_store.delete_collection("test_new_collection")


@pytest.mark.asyncio
async def test_add_documents(milvus_store):
    documents = create_test_documents()
    result = milvus_store.add_documents("test_collection", documents)
    assert len(result) == 3
    assert result[0] == "doc1"


@pytest.mark.asyncio
async def test_query_documents(milvus_store):
    documents = create_test_documents()
    milvus_store.add_documents("test_collection", documents)
    embeddings = get_embeddings("Hello world")
    query_result = milvus_store.query(
        "test_collection", QueryWithEmbedding(text="Hello world", vectors=embeddings)
    )
    assert query_result is not None
    assert len(query_result) > 0


@pytest.mark.asyncio
async def test_retrieve_documents_with_string_query(milvus_store):
    documents = create_test_documents()
    result = milvus_store.add_documents("test_collection", documents)
    assert len(result) == 3
    query_results = milvus_store.retrieve_documents("Hello world", "test_collection")
    assert query_results is not None
    assert len(query_results) > 0
    for query_result in query_results:
        assert query_result.data is not None


@pytest.mark.asyncio
async def test_retrieve_documents_with_query_embedding(milvus_store):
    documents = create_test_documents()
    result = milvus_store.add_documents("test_collection", documents)
    assert len(result) == 3
    query_embedding = QueryWithEmbedding(
        text="Hello world", vectors=get_embeddings("Hello world")
    )
    query_results = milvus_store.retrieve_documents(query_embedding, "test_collection")
    assert query_results is not None
    assert len(query_results) > 0
    for query_result in query_results:
        assert query_result.data is not None
        assert len(query_result.data) > 0


def test_save_embeddings_to_file(tmp_path):
    store = MilvusStore()
    embeddings = get_embeddings("Hello world")
    file_path = tmp_path / "embeddings.json"
    store.save_embeddings_to_file(embeddings, str(file_path))
    with open(file_path, "r") as f:
        loaded_embeddings = json.load(f)
    assert loaded_embeddings == embeddings


@pytest.mark.asyncio
async def test_delete_documents_by_id(milvus_store):
    documents = create_test_documents()
    milvus_store.add_documents("test_collection", documents)
    milvus_store.delete_documents(["doc1", "doc2"], "test_collection")
    query_result = milvus_store.query(
        "test_collection",
        QueryWithEmbedding(text="Hello world", vectors=get_embeddings("Hello world")),
    )
    assert all(
        chunk.chunk_id != "1" for result in query_result for chunk in result.data
    )


@pytest.mark.asyncio
async def test_delete_all_documents(milvus_store):
    documents = create_test_documents()
    milvus_store.add_documents("test_collection", documents)
    milvus_store.delete_collection("test_collection")
    # Attempting to query the deleted collection should raise an exception
    with pytest.raises(MilvusException) as excinfo:
        milvus_store.query(
            "test_collection",
            QueryWithEmbedding(
                text="Hello world", vectors=get_embeddings("Hello world")
            ),
        )
    assert "collection not found" in str(excinfo.value)


def test_get_collection(milvus_store):
    collection = milvus_store.collection
    assert collection is not None


if __name__ == "__main__":
    pytest.main()
