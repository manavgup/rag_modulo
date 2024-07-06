import os
from contextlib import asynccontextmanager
import pytest
from vectordbs.factory import get_datastore
from .test_base_store import BaseStoreTest
from config import settings
EMBEDDING_MODEL = settings.embedding_model
VECTOR_INDEX = settings.collection_name

@pytest.mark.parametrize("vector_db", ["chromadb", "milvus", "weaviate", "pinecone", "elasticsearch"])
class TestVectorStore(BaseStoreTest):

    @pytest.fixture
    @asynccontextmanager
    async def store(self, vector_db):
        store = get_datastore(vector_db)
        await store.create_collection_async(
            VECTOR_INDEX, {"embedding_model": EMBEDDING_MODEL}
        )
        store.collection_name = VECTOR_INDEX
        yield store
        try:
            await store.delete_collection_async(VECTOR_INDEX)
        except Exception as e:
            print(f"Error occurred during teardown: {str(e)}")

    @pytest.mark.asyncio
    async def test_aenter_aexit(self, vector_db):
        async with get_datastore(vector_db) as store:
            assert isinstance(store, get_datastore(vector_db).__class__)