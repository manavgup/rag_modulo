import unittest
from unittest.mock import patch, MagicMock
import numpy as np
from backend.rag_solution.retrieval.retriever import VectorRetriever, KeywordRetriever, HybridRetriever, Retriever

class TestRetriever(unittest.TestCase):

    @patch('backend.rag_solution.retrieval.retriever.SentenceTransformer')
    def test_vector_retriever(self, mock_sentence_transformer):
        mock_model = MagicMock()
        mock_model.encode.return_value = [np.array([0.1, 0.2, 0.3])]
        mock_sentence_transformer.return_value = mock_model

        mock_vector_store = MagicMock()
        mock_vector_store.search.return_value = [
            MagicMock(id=1, payload={'content': 'test content 1'}, score=0.9),
            MagicMock(id=2, payload={'content': 'test content 2'}, score=0.8)
        ]

        retriever = VectorRetriever(mock_vector_store)
        results = retriever.retrieve("test query", k=2)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['id'], 1)
        self.assertEqual(results[0]['content'], 'test content 1')
        self.assertEqual(results[0]['score'], 0.9)

    def test_keyword_retriever(self):
        documents = [
            {"id": 1, "content": "This is a test document"},
            {"id": 2, "content": "Another test document with different content"}
        ]
        retriever = KeywordRetriever(documents)
        results = retriever.retrieve("test document", k=2)

        self.assertEqual(len(results), 2)
        self.assertTrue(all(r['id'] in [1, 2] for r in results))

    @patch('backend.rag_solution.retrieval.retriever.VectorRetriever')
    @patch('backend.rag_solution.retrieval.retriever.KeywordRetriever')
    def test_hybrid_retriever(self, mock_keyword_retriever, mock_vector_retriever):
        mock_vector_retriever.return_value.retrieve.return_value = [
            {"id": 1, "content": "Vector content 1", "score": 0.9},
            {"id": 2, "content": "Vector content 2", "score": 0.8}
        ]
        mock_keyword_retriever.return_value.retrieve.return_value = [
            {"id": 2, "content": "Keyword content 2", "score": 0.85},
            {"id": 3, "content": "Keyword content 3", "score": 0.75}
        ]

        mock_vector_store = MagicMock()
        documents = [{"id": i, "content": f"Content {i}"} for i in range(1, 4)]

        retriever = HybridRetriever(mock_vector_store, documents, vector_weight=0.7)
        results = retriever.retrieve("test query", k=3)

        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]['id'], 2)  # Should be ranked highest due to presence in both results
        self.assertTrue(all(r['id'] in [1, 2, 3] for r in results))

    @patch('backend.rag_solution.retrieval.retriever.VectorRetriever')
    @patch('backend.rag_solution.retrieval.retriever.KeywordRetriever')
    @patch('backend.rag_solution.retrieval.retriever.HybridRetriever')
    def test_retriever_factory(self, mock_hybrid, mock_keyword, mock_vector):
        mock_vector_store = MagicMock()
        documents = [{"id": i, "content": f"Content {i}"} for i in range(1, 4)]

        # Test hybrid retriever
        config = {'use_hybrid': True, 'vector_weight': 0.7}
        retriever = Retriever(config, mock_vector_store, documents)
        self.assertIsInstance(retriever.retriever, HybridRetriever)

        # Test vector retriever
        config = {'use_hybrid': False, 'use_vector': True}
        retriever = Retriever(config, mock_vector_store, documents)
        self.assertIsInstance(retriever.retriever, VectorRetriever)

        # Test keyword retriever
        config = {'use_hybrid': False, 'use_vector': False}
        retriever = Retriever(config, mock_vector_store, documents)
        self.assertIsInstance(retriever.retriever, KeywordRetriever)

if __name__ == '__main__':
    unittest.main()