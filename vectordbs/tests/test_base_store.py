import pytest
from datetime import datetime
from vectordbs.data_types import (
    Document,
    DocumentChunk,
    DocumentChunkMetadata,
    QueryWithEmbedding,
    Source,
)
from vectordbs.utils.watsonx import get_embeddings


class BaseStoreTest:
    """
    Test class for the BaseStore.
    """

    @pytest.fixture
    def store(self):
        raise NotImplementedError(
            "Subclasses must implement the \
            'store' fixture"
        )

    def create_test_documents(self):
        text1 = "Hello world"
        text2 = "Hello Jello"
        text3 = "Tic Tac Toe"
        return [
            Document(
                document_id="doc1",
                name="Doc 1",
                chunks=[
                    DocumentChunk(
                        chunk_id="1",
                        text=text1,
                        vectors=get_embeddings(text1),
                        metadata=DocumentChunkMetadata(
                            source=Source.WEBSITE,
                            created_at=datetime.now().isoformat() + "Z",
                        ),
                    )
                ],
            ),
            Document(
                document_id="doc2",
                name="Doc 2",
                chunks=[
                    DocumentChunk(
                        chunk_id="2",
                        text=text2,
                        vectors=get_embeddings(text2),
                        metadata=DocumentChunkMetadata(
                            source=Source.WEBSITE,
                            created_at=datetime.now().isoformat() + "Z",
                        ),
                    )
                ],
            ),
            Document(
                document_id="doc3",
                name="Doc 3",
                chunks=[
                    DocumentChunk(
                        chunk_id="3",
                        text=text3,
                        vectors=get_embeddings(text3),
                        metadata=DocumentChunkMetadata(
                            source=Source.WEBSITE,
                            created_at=datetime.now().isoformat() + "Z",
                        ),
                    )
                ],
            ),
        ]

    def test_add_documents(self, store):
        documents = self.create_test_documents()
        result = store.add_documents(store.collection_name, documents)
        assert len(result) == 3

    def test_query_documents(self, store):
        documents = self.create_test_documents()
        store.add_documents(store.collection_name, documents)
        embeddings = get_embeddings("Hello world")
        query_result = store.query(
            store.collection_name,
            QueryWithEmbedding(text="Hello world", vectors=embeddings),
        )
        assert query_result is not None
        assert len(query_result) > 0

    def test_retrieve_documents_with_string_query(self, store):
        documents = self.create_test_documents()
        store.add_documents(store.collection_name, documents)
        query_results = store.retrieve_documents("Hello world", 
                                                 store.collection_name)
        assert query_results is not None
        assert len(query_results) > 0
        for query_result in query_results:
            assert query_result.data is not None
            assert len(query_result.data) > 0

    def test_delete_all_documents(self, store):
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
