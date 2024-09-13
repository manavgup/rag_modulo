from contextlib import contextmanager

import pytest
from backend.vectordbs.chroma_store import ChromaDBStore

from backend.core.config import settings
from backend.tests.vectordbs.test_base_store import BaseStoreTest

EMBEDDING_MODEL = settings.embedding_model
CHROMA_INDEX = settings.collection_name

@pytest.mark.chromadb
class TestChromaDBStore(BaseStoreTest):
    store_class = ChromaDBStore

    @pytest.fixture
    @contextmanager
    def store(self):
        store = ChromaDBStore()
        store.create_collection(CHROMA_INDEX, {"embedding_model": EMBEDDING_MODEL})
        store.collection_name = CHROMA_INDEX
        yield store
        try:
            store.delete_collection(CHROMA_INDEX)
        except Exception as e:
            print(f"Error occurred during teardown: {str(e)}")
