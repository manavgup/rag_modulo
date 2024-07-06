import os
from contextlib import asynccontextmanager

import pytest

from vectordbs.chroma_store import ChromaDBStore

from .test_base_store import BaseStoreTest
from config import settings
EMBEDDING_MODEL = settings.embedding_model
CHROMA_INDEX = settings.collection_name

@pytest.mark.chromadb
class TestChromaDBStore(BaseStoreTest):
    store_class = ChromaDBStore

    @pytest.fixture
    @asynccontextmanager
    async def store(self):
        store = ChromaDBStore()
        await store.create_collection_async(
            CHROMA_INDEX, {"embedding_model": EMBEDDING_MODEL}
        )
        store.collection_name = CHROMA_INDEX
        yield store
        try:
            await store.delete_collection_async(CHROMA_INDEX)
        except Exception as e:
            print(f"Error occurred during teardown: {str(e)}")
