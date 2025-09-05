from contextlib import contextmanager
from typing import Any

import pytest


@pytest.mark.chromadb
@pytest.mark.integration
class TestChromaDBStore:
    @pytest.fixture
    @contextmanager
    def store(self, chroma_store: Any) -> Any:
        yield chroma_store

    def test_chroma_store_integration(self: Any, store: Any) -> None:
        """Test basic operations on the Chroma DB store."""
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

    def test_chroma_store_errors(self: Any, store: Any) -> None:
        """Test error handling in the Chroma DB store."""
        with pytest.raises(ValueError):
            store.get_document_by_id("non-existent-id")

        with pytest.raises(ValueError):
            store.delete_document_by_id("non-existent-id")
