import os
import pytest
from vectordbs.chroma_store import ChromaDBStore
from vectordbs.tests.test_base_store import BaseStoreTest

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL",
                            "sentence-transformers/all-minilm-l6-v2")
CHROMA_INDEX = "test_chromadb_collection"


class TestChromaDBStore(BaseStoreTest):
    # Add this line to define the store_class attribute
    store_class = ChromaDBStore

    @pytest.fixture
    def store(self):
        store = ChromaDBStore()
        store.create_collection(CHROMA_INDEX, EMBEDDING_MODEL)
        yield store
        try:
            store.delete_collection(CHROMA_INDEX)
        except Exception as e:
            # Handle the case where the collection may not exist
            print(f"Error occurred during teardown: {str(e)}")
            pass

    # Add any ChromaDB-specific test cases here
