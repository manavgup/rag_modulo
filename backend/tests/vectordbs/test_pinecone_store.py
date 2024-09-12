from contextlib import contextmanager

import pytest

from backend.core.config import settings
from backend.tests.vectordbs.test_base_store import BaseStoreTest
from backend.vectordbs.pinecone_store import PineconeStore

PINECONE_INDEX = settings.collection_name

@pytest.mark.pinecone
class TestPineconeStore(BaseStoreTest):
    store_class = PineconeStore

    @pytest.fixture
    @contextmanager
    def store(self):
        store = PineconeStore()
        store.create_collection(PINECONE_INDEX, {"embedding_model": settings.embedding_model})
        store.collection_name = PINECONE_INDEX
        yield store
        try:
            store.delete_collection(PINECONE_INDEX)
        except Exception as e:
            print(f"Error occurred during teardown: {str(e)}")
