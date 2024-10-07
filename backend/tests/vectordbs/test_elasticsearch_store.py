from contextlib import contextmanager

import pytest

from core.config import settings
from tests.vectordbs.test_base_store import BaseStoreTest
from vectordbs.elasticsearch_store import ElasticSearchStore

ELASTIC_INDEX = settings.collection_name

@pytest.mark.elasticsearch
class TestElasticsearchStore(BaseStoreTest):
    store_class = ElasticSearchStore

    @pytest.fixture
    @contextmanager
    def store(self):
        store = ElasticSearchStore()
        store.create_collection(ELASTIC_INDEX, {"embedding_model": settings.embedding_model})
        store.collection_name = ELASTIC_INDEX
        yield store
        try:
            store.delete_collection(ELASTIC_INDEX)
        except Exception as e:
            print(f"Error occurred during teardown: {str(e)}")
