import json
from datetime import datetime

import pytest

from vectordbs.data_types import (Document, DocumentChunk,
                                  DocumentChunkMetadata,
                                  DocumentMetadataFilter, Embeddings,
                                  QueryWithEmbedding, Source)
from vectordbs.utils.watsonx import get_embeddings
from vectordbs.weaviate_store import WeaviateDataStore


@pytest.fixture
def weaviate_store():
    store = WeaviateDataStore()
    store.create_collection("test_collection")
    yield store
    store.delete_collection("test_collection")


@pytest.mark.asyncio
async def test_add_documents(weaviate_store):
    documents = [
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
        )
    ]
    result = await weaviate_store.add_documents("test_collection", documents)
    assert len(result) == 1
    assert result[0] == "doc1"


@pytest.mark.asyncio
async def test_query_documents(weaviate_store):
    documents = [
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
        )
    ]
    await weaviate_store.add_documents("test_collection", documents)

    embeddings = get_embeddings("Hello world")

    query_result = weaviate_store.query(
        "test_collection", QueryWithEmbedding(text="Hello world", vectors=embeddings)
    )
    assert query_result is not None
    assert len(query_result) > 0


@pytest.mark.asyncio
async def test_retrieve_documents_with_string_query(weaviate_store):
    documents = [
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
    result = await weaviate_store.add_documents("test_collection", documents)
    assert len(result) == 3
    query_results = weaviate_store.retrieve_documents("Hello world", "test_collection")
    assert query_results is not None
    assert len(query_results) > 0

    for query_result in query_results:
        assert query_result.data is not None
        assert len(query_result.data) > 0


@pytest.mark.asyncio
async def test_retrieve_documents_with_query_embedding(weaviate_store):
    documents = [
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
        )
    ]
    result = await weaviate_store.add_documents("test_collection", documents)
    assert len(result) == 1

    query_embedding = QueryWithEmbedding(
        text="Hello world", vectors=get_embeddings("Hello world")
    )
    query_results = weaviate_store.retrieve_documents(
        query_embedding, "test_collection"
    )

    assert query_results is not None
    assert len(query_results) > 0

    for query_result in query_results:
        assert query_result.data is not None
        assert len(query_result.data) > 0


def test_get_collection(weaviate_store):
    collection = weaviate_store.get_collection("test_collection")
    assert collection is not None


def test_create_collection(weaviate_store):
    weaviate_store.create_collection("test_new_collection")
    collection = weaviate_store.get_collection("test_new_collection")
    assert collection is not None
    weaviate_store.delete_collection("test_new_collection")


def test_save_embeddings_to_file(tmp_path):
    store = WeaviateDataStore()
    embeddings = get_embeddings("Hello world")
    file_path = tmp_path / "embeddings.json"
    store.save_embeddings_to_file(embeddings, str(file_path))
    with open(file_path, "r") as f:
        loaded_embeddings = json.load(f)
    assert loaded_embeddings == embeddings


@pytest.mark.asyncio
async def test_delete_documents_by_id(weaviate_store):
    documents = [
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
        )
    ]
    await weaviate_store.add_documents("test_collection", documents)
    await weaviate_store.delete("test_collection", ids=["doc1"])
    query_result = weaviate_store.query(
        "test_collection",
        QueryWithEmbedding(text="Hello world", vectors=get_embeddings("Hello world")),
    )
    assert len(query_result) == 0


@pytest.mark.asyncio
async def test_delete_all_documents(weaviate_store):
    documents = [
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
        )
    ]
    await weaviate_store.add_documents("test_collection", documents)
    await weaviate_store.delete("test_collection", delete_all=True)
    # Attempting to query the deleted collection should raise an exception
    with pytest.raises(Exception) as excinfo:
        weaviate_store.query(
            "test_collection",
            QueryWithEmbedding(
                text="Hello world", vectors=get_embeddings("Hello world")
            ),
        )
    assert "could not find class Test_collection in schema" in str(excinfo.value)
