from contextlib import asynccontextmanager

import pytest

from vectordbs.milvus_store import MilvusStore

from .test_base_store import BaseStoreTest
from config import settings

MILVUS_INDEX=settings.collection_name
EMBEDDING_MODEL=settings.embedding_model

@pytest.mark.milvus
class TestMilvusStore(BaseStoreTest):
    store_class = MilvusStore

    @pytest.fixture
    @asynccontextmanager
    async def store(self):
        store = MilvusStore()
        await store.delete_collection_async(MILVUS_INDEX)
        await store.create_collection_async(
            MILVUS_INDEX, EMBEDDING_MODEL
        )
        yield store
        await store.delete_collection_async("test_milvus_collection")

    # Add any Milvus-specific test cases here
