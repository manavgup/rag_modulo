from datetime import datetime

import pytest
from vectordbs.data_types import (Document, DocumentChunk,
                                  DocumentChunkMetadata, QueryWithEmbedding,
                                  Source)
from vectordbs.error_types import CollectionError
from vectordbs.utils.watsonx import get_embeddings


class BaseStoreTest:
    """
    Test class for the BaseStore.
    """

    @pytest.fixture
    def store(self):
        """
        Fixture to provide an instance of the vector store for testing.
        Subclasses must either implement this fixture or define a `store_class` attribute.
        """
        if hasattr(self, "store_class"):
            with self.store_class() as store:
                yield store
        else:
            raise NotImplementedError(
                "Subclasses must either implement the 'store' fixture or define a 'store_class' attribute."
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
        with store as s:
            result = s.add_documents(s.collection_name, documents)
            assert len(result) == 3

    def test_query_documents(self, store):
        with store as s:
            documents = self.create_test_documents()
            s.add_documents(s.collection_name, documents)
            embeddings = get_embeddings("Hello world")
            query_result = s.query(
                s.collection_name,
                QueryWithEmbedding(text="Hello world", vectors=embeddings),
            )
            assert query_result is not None
            assert len(query_result) > 0

    def test_retrieve_documents_with_string_query(self, store):
        with store as s:
            documents = self.create_test_documents()
            s.add_documents(s.collection_name, documents)
            query_results = s.retrieve_documents(
                "Hello world", s.collection_name
            )
            assert query_results is not None
            assert len(query_results) > 0
            for query_result in query_results:
                assert query_result.data is not None
                assert len(query_result.data) > 0

    def test_delete_all_documents(self, store):
        with store as s:
            documents = self.create_test_documents()
            s.add_documents(s.collection_name, documents)
            s.delete_collection(s.collection_name)
            with pytest.raises(CollectionError):
                s.retrieve_documents(
                    "Hello world", collection_name=s.collection_name
                )

    def test_aenter_aexit(self):
        with self.store_class() as store:
            assert isinstance(store, self.store_class)
