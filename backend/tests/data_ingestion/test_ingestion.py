# tests/test_ingestion.py
import time
from datetime import datetime

import pytest

from core.config import settings
from rag_solution.data_ingestion.ingestion import (
    ingest_documents, process_and_store_document)
from vectordbs.data_types import (Document, DocumentChunk,
                                          DocumentChunkMetadata, Source)
from vectordbs.factory import get_datastore
from vectordbs.utils.watsonx import get_embeddings

# Create a unique collection name for testing
timestamp = int(time.time())  # Get the timestamp as an integer
collection_name = f"test_collection_{timestamp}"

text = "This is a sample document."
sample_document = Document(
    document_id="doc3",
    name="Doc 3",
    chunks=[
        DocumentChunk(
            chunk_id="3",
            text=text,
            vectors=get_embeddings(text),
            metadata=DocumentChunkMetadata(
                source=Source.WEBSITE,
                created_at=datetime.now().isoformat() + "Z",
            ),
        )
    ],
)


@pytest.fixture(scope="module")
def vector_store_with_collection():
    vector_store = get_datastore(settings.vector_db)
    vector_store.create_collection(collection_name)
    yield vector_store
    # Cleanup after tests
    vector_store.delete_collection(collection_name)


@pytest.mark.asyncio
def test_process_and_store_document(vector_store_with_collection):
    process_and_store_document(
        sample_document, vector_store_with_collection, collection_name
    )
    stored_docs = vector_store_with_collection.retrieve_documents(
        "sample", collection_name
    )
    assert len(stored_docs) == 1


@pytest.mark.asyncio
def test_ingest_documents(vector_store_with_collection):
    ingest_documents(
        settings.data_dir, vector_store_with_collection, collection_name
    )
    # Assuming some documents are present in the data_dir
    stored_docs = vector_store_with_collection.retrieve_documents(
        "ROI", collection_name, number_of_results=2
    )
    assert len(stored_docs) > 0
