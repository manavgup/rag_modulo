import pytest
from contextlib import asynccontextmanager
from vectordbs.milvus_store import MilvusStore
from .test_base_store import BaseStoreTest


class TestMilvusStore(BaseStoreTest):
    store_class = MilvusStore

    @pytest.fixture
    @asynccontextmanager
    async def store(self):
        store = MilvusStore()
        await store.delete_collection_async("test_milvus_collection")
        await store.create_collection_async("test_milvus_collection",
                                            "sentence-transformers/all-minilm-l6-v2")
        yield store
        await store.delete_collection_async("test_milvus_collection")

    # Add any Milvus-specific test cases here