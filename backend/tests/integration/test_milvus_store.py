from contextlib import contextmanager

import pytest
from vectordbs.milvus_store import MilvusStore

from core.config import settings

@pytest.mark.milvus
class TestMilvusStore:
    @pytest.fixture
    @contextmanager
    def store(self, milvus_store):
        yield milvus_store

    def test_milvus_store_integration(self, store):
        """Test basic operations on the Milvus store."""
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

    def test_milvus_store_errors(self, store):
        """Test error handling in the Milvus store."""
        with pytest.raises(ValueError):
            store.get_document_by_id("non-existent-id")

        with pytest.raises(ValueError):
            store.delete_document_by_id("non-existent-id")
