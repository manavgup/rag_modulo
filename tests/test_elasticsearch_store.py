import pytest
from contextlib import asynccontextmanager
from vectordbs.elasticsearch_store import ElasticSearchStore
from .test_base_store import BaseStoreTest

ELASTICSEARCH_INDEX = "test_elasticsearch_index"


class TestElasticSearchStore(BaseStoreTest):
    store_class = ElasticSearchStore

    @pytest.fixture
    @asynccontextmanager
    async def store(self):
        store = self.store_class()
        await store.create_collection_async(ELASTICSEARCH_INDEX)
        store.collection_name = ELASTICSEARCH_INDEX
        try:
            yield store
        finally:
            await store.delete_collection_async(ELASTICSEARCH_INDEX)
            await store.client.close()
