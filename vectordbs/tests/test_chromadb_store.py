import os
import pytest
from contextlib import asynccontextmanager
from vectordbs.chroma_store import ChromaDBStore
from vectordbs.tests.test_base_store import BaseStoreTest

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-minilm-l6-v2")
CHROMA_INDEX = "test_chromadb_collection"


class TestChromaDBStore(BaseStoreTest):
    store_class = ChromaDBStore

    @pytest.fixture
    @asynccontextmanager
    async def store(self):
        store = ChromaDBStore()
        await store.create_collection_async(CHROMA_INDEX, {"embedding_model": EMBEDDING_MODEL})
        store.collection_name = CHROMA_INDEX
        yield store
        try:
            await store.delete_collection_async(CHROMA_INDEX)
        except Exception as e:
            print(f"Error occurred during teardown: {str(e)}")
