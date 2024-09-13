import unittest
from unittest.mock import patch, MagicMock
from backend.rag_solution.pipeline.pipeline import Pipeline

class TestPipeline(unittest.TestCase):

    @patch('backend.rag_solution.pipeline.pipeline.QueryRewriter')
    @patch('backend.rag_solution.pipeline.pipeline.Retriever')
    @patch('backend.rag_solution.pipeline.pipeline.Generator')
    @patch('backend.rag_solution.pipeline.pipeline.get_vectorstore')
    def setUp(self, mock_get_vectorstore, mock_generator, mock_retriever, mock_query_rewriter):
        self.mock_query_rewriter = mock_query_rewriter.return_value
        self.mock_retriever = mock_retriever.return_value
        self.mock_generator = mock_generator.return_value
        self.mock_vector_store = mock_get_vectorstore.return_value

        self.config = {
            'query_rewriting': {'use_simple_rewriter': True},
            'retrieval': {'use_hybrid': True},
            'generation': {'type': 'huggingface'},
            'vector_store': 'milvus',
            'top_k': 5
        }

        self.pipeline = Pipeline(self.config)

    def test_pipeline_process(self):
        # Mock the behavior of each component
        self.mock_query_rewriter.rewrite.return_value = "rewritten query"
        self.mock_retriever.retrieve.return_value = [
            {"id": 1, "content": "retrieved content 1", "score": 0.9},
            {"id": 2, "content": "retrieved content 2", "score": 0.8}
        ]
        self.mock_generator.generate.return_value = "generated response"

        # Test the pipeline process
        query = "test query"
        result = self.pipeline.process(query)

        # Check if each component was called with the expected arguments
        self.mock_query_rewriter.rewrite.assert_called_once_with(query, None)
        self.mock_retriever.retrieve.assert_called_once_with("rewritten query", k=5)
        self.mock_generator.generate.assert_called_once_with("rewritten query", self.mock_retriever.retrieve.return_value)

        # Check the structure and content of the result
        self.assertEqual(result['original_query'], query)
        self.assertEqual(result['rewritten_query'], "rewritten query")
        self.assertEqual(result['retrieved_documents'], self.mock_retriever.retrieve.return_value)
        self.assertEqual(result['response'], "generated response")

    def test_pipeline_with_context(self):
        context = {"additional_info": "test context"}
        query = "test query with context"

        self.pipeline.process(query, context)

        # Check if query rewriter was called with the context
        self.mock_query_rewriter.rewrite.assert_called_once_with(query, context)

    @patch('backend.rag_solution.pipeline.pipeline.Pipeline._load_documents')
    def test_pipeline_initialization(self, mock_load_documents):
        mock_load_documents.return_value = [
            {"id": 1, "content": "test document 1"},
            {"id": 2, "content": "test document 2"}
        ]

        pipeline = Pipeline(self.config)

        # Check if components were initialized with correct arguments
        self.mock_query_rewriter.assert_called_once_with(self.config.get('query_rewriting', {}))
        self.mock_retriever.assert_called_once_with(self.config.get('retrieval', {}), self.mock_vector_store, mock_load_documents.return_value)
        self.mock_generator.assert_called_once_with(self.config.get('generation', {}))

if __name__ == '__main__':
    unittest.main()