import unittest
from unittest.mock import MagicMock

from rag_solution.data_ingestion.ingestion import DocumentStore
from rag_solution.retrieval.retriever import HybridRetriever, KeywordRetriever, VectorRetriever
from vectordbs.data_types import Document, QueryResult


class TestRetriever(unittest.TestCase):
    def setUp(self):
        self.mock_vector_store = MagicMock()
        self.mock_document_store = DocumentStore(self.mock_vector_store, "test_collection")

    def test_vector_retriever(self):
        # Setup mock return value for vector store
        mock_results = [
            QueryResult(document=Document(id="1", content="test content 1"), score=0.9),
            QueryResult(document=Document(id="2", content="test content 2"), score=0.8),
        ]
        self.mock_vector_store.retrieve_documents.return_value = mock_results

        # Create retriever and test
        retriever = VectorRetriever(self.mock_document_store)
        results = retriever.retrieve("test_collection", "test query", number_of_results=2)

        # Verify results
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].document.id, "1")
        self.assertEqual(results[0].document.content, "test content 1")
        self.assertEqual(results[0].score, 0.9)

        # Verify vector store was called correctly
        self.mock_vector_store.retrieve_documents.assert_called_once_with(
            "test query", "test_collection", number_of_results=2
        )

    def test_keyword_retriever(self):
        # Setup mock documents
        mock_docs = [
            Document(id="1", content="This is a test document"),
            Document(id="2", content="Another test document with different content"),
        ]
        self.mock_document_store.get_documents = MagicMock(return_value=mock_docs)

        # Create retriever and test
        retriever = KeywordRetriever(self.mock_document_store)
        results = retriever.retrieve("test_collection", "test document", number_of_results=2)

        # Verify results
        self.assertEqual(len(results), 2)
        self.assertTrue(all(isinstance(r, QueryResult) for r in results))
        self.assertTrue(all(r.document.id in ["1", "2"] for r in results))

    def test_hybrid_retriever(self):
        # Setup mock results for vector retriever
        vector_results = [
            QueryResult(document=Document(id="1", content="Vector content 1"), score=0.9),
            QueryResult(document=Document(id="2", content="Vector content 2"), score=0.8),
        ]
        self.mock_vector_store.retrieve_documents.return_value = vector_results

        # Setup mock documents for keyword retriever
        mock_docs = [Document(id="2", content="Keyword content 2"), Document(id="3", content="Keyword content 3")]
        self.mock_document_store.get_documents = MagicMock(return_value=mock_docs)

        # Create retriever and test
        retriever = HybridRetriever(self.mock_document_store, vector_weight=0.7)
        results = retriever.retrieve("test_collection", "test query", number_of_results=3)

        # Verify results
        self.assertLessEqual(len(results), 3)
        self.assertTrue(all(isinstance(r, QueryResult) for r in results))
        # Document 2 should be present as it appears in both vector and keyword results
        self.assertTrue(any(r.document.id == "2" for r in results))

    def test_error_handling(self):
        # Test vector retriever error handling
        self.mock_vector_store.retrieve_documents.side_effect = Exception("Test error")
        retriever = VectorRetriever(self.mock_document_store)

        with self.assertRaises(RuntimeError, msg="Vector retriever should raise exception on error"):
            retriever.retrieve("test_collection", "test query")

        # Test keyword retriever error handling
        self.mock_document_store.get_documents.side_effect = Exception("Test error")
        retriever = KeywordRetriever(self.mock_document_store)

        with self.assertRaises(RuntimeError, msg="Keyword retriever should raise exception on error"):
            retriever.retrieve("test_collection", "test query")


if __name__ == "__main__":
    unittest.main()
