from contextlib import contextmanager

import pytest

from core.config import settings

WEAVIATE_COLLECTION = settings.collection_name


@pytest.mark.weaviate
class TestWeaviateStore:
    @pytest.fixture
    @contextmanager
    def store(self, weaviate_store):
        yield weaviate_store

    def test_weaviate_store_integration(self, store):
        """Test basic operations on the Weaviate store."""
        # Add some documents
        doc1 = {"id": "doc1", "text": "This is the first document."}
        doc2 = {"id": "doc2", "text": "This is the second document."}
        store.add_documents([doc1, doc2])

        # Retrieve documents by ID
        retrieved_doc1 = store.get_document_by_id("doc1")
        assert retrieved_doc1 == doc1

        # Search for documents
        results = store.search("document", 1)
        assert len(results) == 1
        assert results[0]["id"] in ["doc1", "doc2"]

        # Delete a document
        store.delete_document_by_id("doc1")
        results = store.search("document", 2)
        assert len(results) == 1
        assert results[0]["id"] == "doc2"

    def test_weaviate_store_errors(self, store):
        """Test error handling in the Weaviate store."""
        with pytest.raises(ValueError):
            store.get_document_by_id("non-existent-id")

        with pytest.raises(ValueError):
            store.delete_document_by_id("non-existent-id")
