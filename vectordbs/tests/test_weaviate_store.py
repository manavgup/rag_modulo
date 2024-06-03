import pytest
from vectordbs.weaviate_store import WeaviateDataStore
from vectordbs.tests.test_base_store import BaseStoreTest
from vectordbs.data_types import QueryWithEmbedding
from vectordbs.utils.watsonx import get_embeddings

WEAVIATE_INDEX = "test_weaviate_index"


class TestWeaviateStore(BaseStoreTest):
    store_class = WeaviateDataStore

    @pytest.fixture
    def store(self):
        store = WeaviateDataStore()
        store.collection_name = "WEAVIATE_INDEX"
        store.create_collection("WEAVIATE_INDEX")
        yield store
        store.delete_collection("WEAVIATE_INDEX")

    # Add any Weaviate-specific test cases here
    @pytest.mark.asyncio
    async def test_add_documents(self, store):
        documents = self.create_test_documents()
        result = await store.add_documents(store.collection_name, documents)
        assert len(result) == 3
        
    @pytest.mark.asyncio
    async def test_query_documents(self, store):
        documents = self.create_test_documents()
        await store.add_documents(store.collection_name, documents)
        embeddings = get_embeddings("Hello world")
        query_result = store.query(
            store.collection_name,
            QueryWithEmbedding(text="Hello world", vectors=embeddings),
        )
        assert query_result is not None
        assert len(query_result) > 0

    @pytest.mark.asyncio
    async def test_retrieve_documents_with_string_query(self, store):
        documents = self.create_test_documents()
        await store.add_documents(store.collection_name, documents)
        query_results = store.retrieve_documents("Hello world",
                                                 store.collection_name)
        assert query_results is not None
        assert len(query_results) > 0
        for query_result in query_results:
            assert query_result.data is not None
            assert len(query_result.data) > 0

    @pytest.mark.asyncio
    async def test_delete_all_documents(self, store):
        documents = self.create_test_documents()
        store.add_documents(store.collection_name, documents)
        store.delete_collection(store.collection_name)
        with pytest.raises(Exception):
            store.retrieve_documents(
                QueryWithEmbedding(
                    text="Hello world", vectors=get_embeddings("Hello world")
                ),
                store.collection_name,
            )

    @pytest.mark.asyncio
    async def test_aenter_aexit(self):
        async with self.store_class() as store:
            assert isinstance(store, self.store_class)
