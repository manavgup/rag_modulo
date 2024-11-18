import unittest
from rag_solution.pipeline.pipeline import Pipeline, PipelineResult
from vectordbs.data_types import Document, QueryResult
from typing import List
import os

class TestPipeline(unittest.TestCase):
    def setUp(self):
        """Set up test pipeline with real components"""
        self.config = {
            'query_rewriting': {
                'use_simple_rewriter': True
            },
            'retrieval': {
                'type': 'hybrid',
                'vector_weight': 0.7
            },
            'generation': {
                'type': 'watsonx',
                'model_name': os.getenv('TEST_LLM_MODEL', 'google/flan-t5-base'),
                'default_params': {
                    'max_new_tokens': 100,
                    'min_new_tokens': 1,
                    'temperature': 0.7,
                    'top_k': 5
                }
            },
            'vector_store': {
                'type': 'milvus',
                'connection_args': {
                    'host': os.getenv('TEST_MILVUS_HOST', 'localhost'),
                    'port': os.getenv('TEST_MILVUS_PORT', '19530')
                }
            },
            'collection_name': 'test_collection',
            'chunking': {
                'strategy': 'sentence',
                'min_chunk_size': 100,
                'max_chunk_size': 500,
                'chunk_overlap': 50
            },
            'embedding': {
                'model': 'watsonx',
                'dimension': 768,
                'field': 'text_vector'
            }
        }
        
        # Create pipeline instance
        self.pipeline = Pipeline(self.config)

    def test_pipeline_process_simple_query(self):
        """Test pipeline with a simple query on test documents"""
        # Test data
        test_documents = [
            Document(id="1", content="Python is a high-level programming language known for its simplicity and readability."),
            Document(id="2", content="Machine learning is a subset of artificial intelligence that enables systems to learn from data."),
            Document(id="3", content="Natural Language Processing (NLP) is used to help computers understand human language.")
        ]
        
        # Initialize pipeline and load test documents
        self.pipeline.document_store.add_documents(test_documents)
        
        # Process a query
        query = "What is Python?"
        result = self.pipeline.process(query, "test_collection")
        
        # Verify result structure and content
        self.assertIsInstance(result, PipelineResult)
        self.assertEqual(result.original_query, query)
        self.assertIsNotNone(result.rewritten_query)
        self.assertIsNotNone(result.generated_answer)
        self.assertGreater(len(result.retrieved_documents), 0)
        
        # Verify the most relevant document was retrieved
        self.assertTrue(any("Python" in doc for doc in result.retrieved_documents))

    def test_pipeline_process_complex_query(self):
        """Test pipeline with a more complex query requiring context understanding"""
        test_documents = [
            Document(id="4", content="RAG (Retrieval Augmented Generation) combines retrieval and generation for better AI responses."),
            Document(id="5", content="Vector databases store and retrieve high-dimensional vectors efficiently."),
            Document(id="6", content="Embeddings are numerical representations of text that capture semantic meaning.")
        ]
        
        self.pipeline.document_store.add_documents(test_documents)
        
        query = "How does RAG work with vector databases?"
        result = self.pipeline.process(query, "test_collection")
        
        self.assertIsInstance(result, PipelineResult)
        self.assertTrue(any("RAG" in doc for doc in result.retrieved_documents))
        self.assertTrue(any("vector" in doc.lower() for doc in result.retrieved_documents))

    def test_pipeline_process_stream(self):
        """Test streaming response from pipeline"""
        test_documents = [
            Document(id="7", content="Streaming allows for real-time data processing and response generation."),
            Document(id="8", content="Chunks of data can be processed and sent incrementally for better user experience.")
        ]
        
        self.pipeline.document_store.add_documents(test_documents)
        
        query = "Explain streaming data processing"
        stream = self.pipeline.process_stream(query, "test_collection")
        
        # Collect stream chunks
        chunks = list(stream)
        
        # Verify stream structure
        self.assertTrue(any('rewritten_query' in chunk for chunk in chunks))
        self.assertTrue(any('response_chunk' in chunk for chunk in chunks))
        
        # Verify content relevance
        response_chunks = [chunk['response_chunk'] for chunk in chunks if 'response_chunk' in chunk]
        combined_response = ''.join(response_chunks)
        self.assertGreater(len(combined_response), 0)

    def test_pipeline_error_handling(self):
        """Test pipeline's error handling capabilities"""
        # Test with empty query
        result = self.pipeline.process("", "test_collection")
        self.assertIn("error", result.evaluation)
        
        # Test with non-existent collection
        result = self.pipeline.process("test query", "non_existent_collection")
        self.assertIn("error", result.evaluation)

    def tearDown(self):
        """Clean up test data"""
        try:
            self.pipeline.document_store.vector_store.delete_collection("test_collection")
        except Exception as e:
            print(f"Error cleaning up test collection: {e}")

if __name__ == '__main__':
    unittest.main()
