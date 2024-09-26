import pytest
from backend.vectordbs.data_types import (Document, DocumentMetadataFilter,
                                  QueryWithEmbedding)
from backend.vectordbs.vector_store import VectorStore


class TestVectorStore:
    """
    A generic test class for VectorStore implementations.
    """

    @pytest.fixture
    def store(self) -> VectorStore:
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

    def test_create_collection(self, store):
        store.create_collection("test_collection")
        assert store.collection_name == "test_collection"

    def test_add_documents(self, store):
        documents = [
            Document(document_id="doc1", name="Document 1", chunks=[]),
            Document(document_id="doc2", name="Document 2", chunks=[])
        ]
        result = store.add_documents("test_collection", documents)
        assert len(result) == len(documents)

    def test_retrieve_documents(self, store):
        query = "test query"
        results = store.retrieve_documents(query, "test_collection")
        assert isinstance(results, list)

    def test_query_documents(self, store):
        embeddings = [0.1, 0.2, 0.3]
        query = QueryWithEmbedding(text="test query", vectors=embeddings)
        results = store.query("test_collection", query)
        assert isinstance(results, list)

    def test_delete_collection(self, store):
        store.create_collection("test_collection")
        store.delete_collection("test_collection")
        with pytest.raises(Exception):
            store.retrieve_documents("test query", "test_collection")

    def test_delete_documents(self, store):
        documents = [
            Document(document_id="doc1", name="Document 1", chunks=[]),
            Document(document_id="doc2", name="Document 2", chunks=[])
        ]
        store.add_documents("test_collection", documents)
        store.delete_documents("test_collection", ["doc1"])
        remaining_docs = store.retrieve_documents("test query", "test_collection")
        assert all(doc.document_id != "doc1" for doc in remaining_docs)