import pytest
from vectordbs.pinecone_store import PineconeStore
from vectordbs.tests.test_base_store import BaseStoreTest

PINECONE_INDEX = "test-pinecone-index"


class TestPineconeStore(BaseStoreTest):
    store_class = PineconeStore

    @pytest.fixture
    def store(self):
        store = PineconeStore()
        store.collection_name = PINECONE_INDEX
        store.create_collection(PINECONE_INDEX,
                                "sentence-transformers/all-minilm-l6-v2")
        yield store
        store.delete_collection(PINECONE_INDEX)

    # Add any Pinecone-specific test cases here
