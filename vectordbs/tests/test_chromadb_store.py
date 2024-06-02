import pytest
from datetime import datetime
from vectordbs.data_types import (
    Document,
    DocumentChunk,
    DocumentChunkMetadata,
    Source,
    QueryWithEmbedding,
    DocumentMetadataFilter,
)
from vectordbs.chroma_store import (
    ChromaDBStore,
)  # Adjust the import as per your project structure
from vectordbs.utils.watsonx import get_embeddings
import logging
import os

CHROMADB_HOST = os.getenv("CHROMADB_HOST", "localhost")
CHROMADB_PORT = int(os.getenv("CHROMADB_PORT", "8000"))
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL", "sentence-transformers/paraphrase-MiniLM-L6-v2"
)
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "384"))


logging.basicConfig(level=logging.INFO)

CHROMA_INDEX = "test-index"  # Assuming you want to use the same index name


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
def chromadb_store():
    store = ChromaDBStore()
    store.create_collection(CHROMA_INDEX, EMBEDDING_MODEL)
    try:
        yield store
    finally:
        try:
            store.delete_collection(CHROMA_INDEX)
        except Exception as e:
            logging.error(f"Failed to delete collection in test teardown: {e}")


def test_create_collection(chromadb_store):
    chromadb_store.create_collection("new-test-index", EMBEDDING_MODEL)
    assert chromadb_store.collection is not None
    chromadb_store.delete_collection("new-test-index")


def test_add_documents(chromadb_store):
    documents = create_test_documents()
    result = chromadb_store.add_documents(CHROMA_INDEX, documents)
    assert len(result) == 3
    assert result[0] == "1"


def test_query_documents(chromadb_store):
    documents = create_test_documents()
    chromadb_store.add_documents(CHROMA_INDEX, documents)

    embeddings = get_embeddings("Hello world")

    query_results = chromadb_store.retrieve_documents(
        QueryWithEmbedding(text="Hello world", vectors=embeddings),
        CHROMA_INDEX,
        limit=10,
    )
    assert query_results is not None
    assert len(query_results) > 0
    for query_result in query_results:
        assert query_result.data is not None
        assert len(query_result.data) > 0


def test_retrieve_documents_with_string_query(chromadb_store):
    documents = create_test_documents()
    result = chromadb_store.add_documents(CHROMA_INDEX, documents)
    assert len(result) == 3
    query_results = chromadb_store.retrieve_documents(
        "Hello world", CHROMA_INDEX, limit=10
    )
    assert query_results is not None
    assert len(query_results) > 0

    for query_result in query_results:
        assert query_result.data is not None
        assert len(query_result.data) > 0


def test_delete_documents(chromadb_store):
    documents = create_test_documents()
    added_ids = chromadb_store.add_documents(CHROMA_INDEX, documents)

    # Delete empty list
    deleted_count = chromadb_store.delete_documents([], CHROMA_INDEX)
    assert deleted_count == 0

    # Delete one document and verify
    chunk_id_to_delete = added_ids[0]
    deleted_count = chromadb_store.delete_documents([chunk_id_to_delete], CHROMA_INDEX)
    assert deleted_count == 1

    # Remove the deleted document from the list of added IDs for the next test
    added_ids.remove(chunk_id_to_delete)

    # Delete non-existent document
    # deleted_count = chromadb_store.delete_documents(["non_existent_id"], CHROMA_INDEX)
    # assert deleted_count == 0  # Assuming deletion attempt on all ids passed

    # Delete all remaining documents
    deleted_count = chromadb_store.delete_documents(added_ids, CHROMA_INDEX)
    assert deleted_count == len(added_ids)  # Check if all remaining were deleted

    delete_from_wrong_index = chromadb_store.delete_documents(added_ids, "wrong_index")
    assert delete_from_wrong_index == 0


def test_delete_all_documents(chromadb_store):
    documents = create_test_documents()
    chromadb_store.add_documents(CHROMA_INDEX, documents)
    # Ensure the collection is deleted only if it exists
    try:
        chromadb_store.delete_collection(CHROMA_INDEX)
    except Exception as e:
        logging.error(f"Failed to delete collection in test teardown: {e}")

    # Attempting to query the deleted collection should raise an exception
    with pytest.raises(ValueError):
        chromadb_store.retrieve_documents(
            QueryWithEmbedding(
                text="Hello world", vectors=get_embeddings("Hello world")
            ),
            CHROMA_INDEX,
            limit=10,
        )


def test_convert_to_chunk():
    store = ChromaDBStore()
    sample_id = "1"
    sample_text = "Sample text"
    sample_vectors = [0.1] * EMBEDDING_DIM
    sample_metadata = {
        "text": sample_text,
        "document_id": "doc1",
        "source": "website",
        "source_id": "source_1",
        "url": "http://example.com",
        "created_at": "2023-01-01T00:00:00Z",
        "author": "Author Name",
    }

    chunk = store._convert_to_chunk(
        id=sample_id, text=sample_text, vectors=sample_vectors, metadata=sample_metadata
    )

    assert chunk.chunk_id == sample_id
    assert chunk.text == sample_text
    assert chunk.vectors == sample_vectors
    assert chunk.metadata.source == Source.WEBSITE
    assert chunk.metadata.source_id == sample_metadata["source_id"]
    assert chunk.metadata.url == sample_metadata["url"]
    assert chunk.metadata.created_at == sample_metadata["created_at"]
    assert chunk.metadata.author == sample_metadata["author"]
    assert chunk.document_id == sample_metadata["document_id"]


def test_process_search_results():
    store = ChromaDBStore()
    sample_response = {
        "ids": [["1"]],
        "distances": [[1.0]],
        "metadatas": [
            [
                {
                    "text": "Sample text",
                    "document_id": "doc1",
                    "source": "website",
                    "source_id": "source_1",
                    "url": "http://example.com",
                    "created_at": "2023-01-01T00:00:00Z",
                    "author": "Author Name",
                }
            ]
        ],
        "documents": [["Sample text"]],
    }
    results = store._process_search_results(sample_response)
    assert len(results) == 1
    assert results[0].data[0].chunk_id == "1"
    assert results[0].data[0].text == "Sample text"
    assert results[0].data[0].metadata.source == Source.WEBSITE
    assert results[0].data[0].metadata.source_id == "source_1"
    assert results[0].data[0].metadata.url == "http://example.com"
    assert results[0].data[0].metadata.created_at == "2023-01-01T00:00:00Z"
    assert results[0].data[0].metadata.author == "Author Name"
    assert results[0].data[0].document_id == "doc1"
    assert results[0].similarities[0] == 1.0


def test_build_filters():
    store = ChromaDBStore()
    filter_eq = DocumentMetadataFilter(
        field_name="author", value="John Doe", operator="eq"
    )
    filters = store._build_filters(filter_eq)
    assert filters == {"author": "John Doe"}


@pytest.mark.asyncio
async def test_aenter_aexit():
    async with ChromaDBStore() as store:
        assert isinstance(store, ChromaDBStore)
