import pytest
from vectordbs.milvus_store import MilvusStore
from vectordbs.tests.test_base_store import BaseStoreTest


class TestMilvusStore(BaseStoreTest):
    # Add this line to define the store_class attribute
    store_class = MilvusStore
    
    @pytest.fixture
    def store(self):
        store = MilvusStore()
        store.collection_name = "test_milvus_collection"
        store.create_collection("test_milvus_collection",
                                "sentence-transformers/all-minilm-l6-v2",
                                client=store.client)
        yield store
        store.delete_collection("test_milvus_collection")

    # Add any Milvus-specific test cases here