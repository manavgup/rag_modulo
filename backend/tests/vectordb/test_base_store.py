from collections.abc import Generator
from datetime import datetime
from typing import Any

import pytest

from vectordbs.data_types import Document, DocumentChunk, DocumentChunkMetadata, Source
from vectordbs.utils.watsonx import get_embeddings
from vectordbs.vector_store import VectorStore


class BaseStoreTest:
    """
    Test class for the BaseStore.
    """

    @pytest.fixture
    def store(self: Any) -> Generator[VectorStore, None, None]:
        """
        Fixture to provide an instance of the vector store for testing.
        Subclasses must either implement this fixture or define a `store_class` attribute.
        """
        if hasattr(self, "store_class"):
            with self.store_class() as store:
                yield store
        else:
            raise NotImplementedError("Subclasses must either implement the 'store' fixture or define a 'store_class' attribute.")

    def create_test_documents(self: Any) -> list[Document]:
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
                        vectors=get_embeddings(text1)[0],
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
                        vectors=get_embeddings(text2)[0],
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
                        vectors=get_embeddings(text3)[0],
                        metadata=DocumentChunkMetadata(
                            source=Source.WEBSITE,
                            created_at=datetime.now().isoformat() + "Z",
                        ),
                    )
                ],
            ),
        ]

    # @pytest.mark.integration
    # def test_add_documents(self, store: VectorStore) -> None:
    #     documents = self.create_test_documents()
    #     result = store.add_documents(store.collection_name, documents)
    #     assert len(result) == 3

    # def test_query_documents(self, store: VectorStore) -> None:
    #     documents = self.create_test_documents()
    #     store.add_documents(store.collection_name, documents)
    #     embeddings = get_embeddings("Hello world")
    #     query_result = store.query(
    #         store.collection_name,
    #         QueryWithEmbedding(text="Hello world", vectors=embeddings[0]),
    #     )
    #     assert query_result is not None
    #     assert len(query_result) > 0

    # def test_retrieve_documents_with_string_query(self, store: VectorStore) -> None:
    # documents = self.create_test_documents()
    # store.add_documents(store.collection_name, documents)
    # query_results = store.retrieve_documents("Hello world", store.collection_name)
    # assert query_results is not None
    # assert len(query_results) > 0
    # for query_result in query_results:
    #     assert query_result.data is not None
    #     assert len(query_result.data) > 0

    # def test_retrieve_documents_with_number_of_results(self, store: VectorStore) -> None:
    # documents = self.create_test_documents()
    # store.add_documents(store.collection_name, documents)
    # # Test with number_of_results=2
    # query_results = store.retrieve_documents("Hello", store.collection_name, number_of_results=2)
    # assert query_results is not None
    # # Should return exactly 2 results
    # assert len(query_results) == 1  # One QueryResult object
    # assert len(query_results[0].data) == 2  # With two documents

    # def test_delete_all_documents(self, store: VectorStore) -> None:
    # documents = self.create_test_documents()
    # store.add_documents(store.collection_name, documents)
    # store.delete_collection(store.collection_name)
    # with pytest.raises(CollectionError):
    #     store.retrieve_documents("Hello world", collection_name=store.collection_name)

    # def test_aenter_aexit(self) -> None:
    #     with self.store_class() as store:
    #         assert isinstance(store, self.store_class)
