from contextlib import contextmanager

import pytest
from backend.vectordbs.milvus_store import MilvusStore

from backend.core.config import settings
from backend.tests.vectordbs.test_base_store import BaseStoreTest

MILVUS_COLLECTION = settings.collection_name

@pytest.mark.milvus
class TestMilvusStore(BaseStoreTest):
    store_class = MilvusStore

    @pytest.fixture
    @contextmanager
    def store(self):
        store = MilvusStore()
        store.create_collection(MILVUS_COLLECTION, {"embedding_model": settings.embedding_model})
        store.collection_name = MILVUS_COLLECTION
        yield store
        try:
            store.delete_collection(MILVUS_COLLECTION)
        except Exception as e:
            print(f"Error occurred during teardown: {str(e)}")
