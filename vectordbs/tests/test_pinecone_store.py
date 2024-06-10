import pytest
from contextlib import asynccontextmanager
from vectordbs.pinecone_store import PineconeStore
from vectordbs.tests.test_base_store import BaseStoreTest

PINECONE_INDEX = "test-pinecone-index"


class TestPineconeStore(BaseStoreTest):
    store_class = PineconeStore

    @pytest.fixture
    @asynccontextmanager
    async def store(self):
        store = PineconeStore()
        store.collection_name = PINECONE_INDEX
        await store.create_collection_async(PINECONE_INDEX,
                                            "sentence-transformers/all-minilm-l6-v2")
        yield store
        await store.delete_collection_async(PINECONE_INDEX)

    # Add any Pinecone-specific test cases here
