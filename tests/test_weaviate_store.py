from contextlib import asynccontextmanager

import pytest

from vectordbs.weaviate_store import WeaviateDataStore

from .test_base_store import BaseStoreTest

from config import settings
WEAVIATE_INDEX = settings.collection_name

@pytest.mark.weaviate
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
