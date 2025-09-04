import unittest
from unittest.mock import MagicMock

from rag_solution.data_ingestion.ingestion import DocumentStore
from rag_solution.retrieval.factories import RetrieverFactory
from rag_solution.retrieval.retriever import HybridRetriever, KeywordRetriever, VectorRetriever


@pytest.mark.atomic
class TestRetrieverFactory(unittest.TestCase):
    def setUp(self):
        self.mock_vector_store = MagicMock()
        self.mock_document_store = DocumentStore(self.mock_vector_store, "test_collection")

    def test_create_hybrid_retriever(self):
        config = {"type": "hybrid", "vector_weight": 0.8}
        retriever = RetrieverFactory.create_retriever(config, self.mock_document_store)

        self.assertIsInstance(retriever, HybridRetriever)
        self.assertEqual(retriever.vector_weight, 0.8)

    def test_create_vector_retriever(self):
        config = {"type": "vector"}
        retriever = RetrieverFactory.create_retriever(config, self.mock_document_store)

        self.assertIsInstance(retriever, VectorRetriever)

    def test_create_keyword_retriever(self):
        config = {"type": "keyword"}
        retriever = RetrieverFactory.create_retriever(config, self.mock_document_store)

        self.assertIsInstance(retriever, KeywordRetriever)

    def test_default_to_hybrid_retriever(self):
        config = {}  # Empty config should default to hybrid
        retriever = RetrieverFactory.create_retriever(config, self.mock_document_store)

        self.assertIsInstance(retriever, HybridRetriever)
        self.assertEqual(retriever.vector_weight, 0.7)  # Default weight

    def test_invalid_retriever_type(self):
        config = {"type": "invalid_type"}
        with self.assertRaises(ValueError) as context:
            RetrieverFactory.create_retriever(config, self.mock_document_store)

        self.assertTrue("Invalid retriever type: invalid_type" in str(context.exception))


if __name__ == "__main__":
    unittest.main()
