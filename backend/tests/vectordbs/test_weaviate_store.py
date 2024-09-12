from contextlib import contextmanager

import pytest

from backend.core.config import settings
from backend.tests.vectordbs.test_base_store import BaseStoreTest
from backend.vectordbs.weaviate_store import WeaviateDataStore

WEAVIATE_COLLECTION = settings.collection_name

@pytest.mark.weaviate
class TestWeaviateStore(BaseStoreTest):
    store_class = WeaviateDataStore

    @pytest.fixture
    @contextmanager
    def store(self):
        store = WeaviateDataStore()
        store.create_collection(WEAVIATE_COLLECTION, {"embedding_model": settings.embedding_model})
        store.collection_name = WEAVIATE_COLLECTION
        yield store
        try:
            store.delete_collection(WEAVIATE_COLLECTION)
        except Exception as e:
            print(f"Error occurred during teardown: {str(e)}")
