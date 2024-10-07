import unittest
from unittest.mock import patch, MagicMock
from rag_solution.generation.generator import Generator, HuggingFaceGenerator, WatsonxGenerator

class TestGenerator(unittest.TestCase):

    def test_huggingface_generator(self):
        config = {'type': 'huggingface', 'model_name': 'gpt2'}
        with patch('rag_solution.generation.generator.pipeline') as mock_pipeline:
            mock_pipeline.return_value = lambda *args, **kwargs: [{'generated_text': 'Answer: Test response'}]
            generator = Generator(config)
            query = "Test query"
            documents = [{"content": "Test content"}]
            response = generator.generate(query, documents)
            self.assertEqual(response, "Test response")

    def test_watsonx_generator(self):
        config = {'type': 'watsonx'}
        with patch('rag_solution.generation.generator.generate_text') as mock_generate_text:
            mock_generate_text.return_value = "Test response"
            generator = Generator(config)
            query = "Test query"
            documents = [{"content": "Test content"}]
            response = generator.generate(query, documents)
            self.assertEqual(response, "Test response")

    def test_invalid_generator_type(self):
        config = {'type': 'invalid'}
        with self.assertRaises(ValueError):
            Generator(config)

if __name__ == '__main__':
    unittest.main()