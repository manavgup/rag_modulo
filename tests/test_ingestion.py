# tests/test_ingestion.py
import time
from datetime import datetime

import pytest
import pytest_asyncio

from config import settings
from rag_solution.data_ingestion.ingestion import (ingest_documents,
                                                   process_and_store_document)
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


@pytest_asyncio.fixture(scope="module")
async def vector_store_with_collection():
    vector_store = get_datastore(settings.vector_db)
    await vector_store.create_collection_async(collection_name)
    yield vector_store
    # Cleanup after tests
    await vector_store.delete_collection_async(collection_name)


@pytest.mark.asyncio
async def test_process_and_store_document(vector_store_with_collection):
    await process_and_store_document(
        sample_document, vector_store_with_collection, collection_name
    )
    stored_docs = await vector_store_with_collection.retrieve_documents_async(
        "sample", collection_name
    )
    assert len(stored_docs) == 1


@pytest.mark.asyncio
async def test_ingest_documents(vector_store_with_collection):
    await ingest_documents(
        settings.data_dir, vector_store_with_collection, collection_name
    )
    # Assuming some documents are present in the data_dir
    stored_docs = await vector_store_with_collection.retrieve_documents_async(
        "ROI", collection_name, limit=2
    )
    assert len(stored_docs) > 0
