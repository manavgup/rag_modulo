import pytest
from vectordbs.weaviate_store import WeaviateDataStore
from vectordbs.tests.test_base_store import BaseStoreTest
from contextlib import asynccontextmanager

WEAVIATE_INDEX = "test_weaviate_index"


class TestWeaviateStore(BaseStoreTest):
    store_class = WeaviateDataStore

    @pytest.fixture
    @asynccontextmanager
    async def store(self):
        store = WeaviateDataStore()
        store.collection_name = WEAVIATE_INDEX
        await store.create_collection_async(WEAVIATE_INDEX)
        try:
            yield store
        finally:
            await store.delete_collection_async(WEAVIATE_INDEX)
    # Add any Weaviate-specific test cases here
