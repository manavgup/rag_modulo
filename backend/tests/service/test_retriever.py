import unittest
from typing import Any
from unittest.mock import MagicMock, patch


from rag_solution.data_ingestion.ingestion import DocumentStore
from rag_solution.retrieval.retriever import HybridRetriever, KeywordRetriever, VectorRetriever
from vectordbs.data_types import Document, DocumentChunk, QueryResult, VectorQuery


class TestRetriever(unittest.TestCase):
    def setUp(self: Any) -> None:
        self.mock_vector_store = MagicMock()
        self.mock_document_store = DocumentStore(self.mock_vector_store, "test_collection")

    def test_vector_retriever(self) -> None:
        # Setup mock return value for vector store
        mock_chunk1 = DocumentChunk(chunk_id="1", text="test content 1")
        mock_chunk2 = DocumentChunk(chunk_id="2", text="test content 2")
        mock_results = [
            QueryResult(chunk=mock_chunk1, score=0.9, embeddings=[]),
            QueryResult(chunk=mock_chunk2, score=0.8, embeddings=[]),
        ]
        self.mock_vector_store.retrieve_documents.return_value = mock_results

        # Create retriever and test
        retriever = VectorRetriever(self.mock_document_store)
        query = VectorQuery(text="test query", number_of_results=2)
        results = retriever.retrieve("test_collection", query)

        # Verify results
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].chunk.chunk_id, "1")
        self.assertEqual(results[0].chunk.text, "test content 1")
        self.assertEqual(results[0].score, 0.9)

        # Verify vector store was called correctly
        self.mock_vector_store.retrieve_documents.assert_called_once_with("test query", "test_collection", number_of_results=2)

    def test_keyword_retriever(self) -> None:
        # Setup mock documents
        mock_chunk1 = DocumentChunk(chunk_id="1", text="This is a test document")
        mock_chunk2 = DocumentChunk(chunk_id="2", text="Another test document with different content")
        mock_docs = [
            Document(name="doc1", document_id="1", chunks=[mock_chunk1]),
            Document(name="doc2", document_id="2", chunks=[mock_chunk2]),
        ]
        with patch.object(self.mock_document_store, "get_documents", return_value=mock_docs):
            # Create retriever and test
            retriever = KeywordRetriever(self.mock_document_store)
            query = VectorQuery(text="test document", number_of_results=2)
            results = retriever.retrieve("test_collection", query)

        # Verify results
        self.assertEqual(len(results), 2)
        self.assertTrue(all(isinstance(r, QueryResult) for r in results))
        self.assertTrue(all(r.chunk.chunk_id in ["1", "2"] for r in results))

    def test_hybrid_retriever(self) -> None:
        # Setup mock results for vector retriever
        mock_chunk1 = DocumentChunk(chunk_id="1", text="Vector content 1")
        mock_chunk2 = DocumentChunk(chunk_id="2", text="Vector content 2")
        vector_results = [
            QueryResult(chunk=mock_chunk1, score=0.9, embeddings=[]),
            QueryResult(chunk=mock_chunk2, score=0.8, embeddings=[]),
        ]
        self.mock_vector_store.retrieve_documents.return_value = vector_results

        # Setup mock documents for keyword retriever
        mock_chunk2_kw = DocumentChunk(chunk_id="2", text="Keyword content 2")
        mock_chunk3 = DocumentChunk(chunk_id="3", text="Keyword content 3")
        mock_docs = [
            Document(name="doc2", document_id="2", chunks=[mock_chunk2_kw]),
            Document(name="doc3", document_id="3", chunks=[mock_chunk3]),
        ]
        with patch.object(self.mock_document_store, "get_documents", return_value=mock_docs):
            # Create retriever and test
            retriever = HybridRetriever(self.mock_document_store, vector_weight=0.7)
            query = VectorQuery(text="test query", number_of_results=3)
            results = retriever.retrieve("test_collection", query)

        # Verify results
        self.assertLessEqual(len(results), 3)
        self.assertTrue(all(isinstance(r, QueryResult) for r in results))
        # Document 2 should be present as it appears in both vector and keyword results
        self.assertTrue(any(r.chunk.chunk_id == "2" for r in results))

    def test_error_handling(self) -> None:
        # Test vector retriever error handling
        self.mock_vector_store.retrieve_documents.side_effect = Exception("Test error")
        retriever = VectorRetriever(self.mock_document_store)
        query = VectorQuery(text="test query", number_of_results=5)

        with self.assertRaises(RuntimeError, msg="Vector retriever should raise exception on error"):
            retriever.retrieve("test_collection", query)

        # Test keyword retriever error handling
        with patch.object(self.mock_document_store, "get_documents", side_effect=Exception("Test error")):
            keyword_retriever = KeywordRetriever(self.mock_document_store)

            with self.assertRaises(RuntimeError, msg="Keyword retriever should raise exception on error"):
                keyword_retriever.retrieve("test_collection", query)


if __name__ == "__main__":
    unittest.main()
