import unittest
from unittest.mock import patch, MagicMock
from rag_solution.generation.generator import WatsonxGenerator,BaseGenerator

class TestGenerator(unittest.TestCase):

    def test_huggingface_generator(self):
        config = {'type': 'huggingface', 'model_name': 'gpt2'}
        with patch('rag_solution.generation.generator.pipeline') as mock_pipeline:
            mock_pipeline.return_value = lambda *args, **kwargs: [{'generated_text': 'Answer: Test response'}]
            generator = BaseGenerator(config)
            query = "Test query"
            documents = [{"content": "Test content"}]
            response = generator.generate(query=query, context="context")
            self.assertEqual(response, "Test response")

    def test_watsonx_generator(self):
        config = {'type': 'watsonx'}
        with patch('rag_solution.generation.generator.generate_text') as mock_generate_text:
            mock_generate_text.return_value = "Test response"
            generator = WatsonxGenerator(config)
            query = "Test query"
            documents = [{"content": "Test content"}]
            response = generator.generate(query=query, context="context")
            self.assertEqual(response, "Test response")


    def test_watsonx_generate_stream(self):
        config = {
        'type': 'watsonx',
        'model_name': 'meta-llama/llama-3-8b-instruct',
        'default_params': {
             'max_new_tokens': 20,
             'temperature': 0.7,
             'random_seed': 50
         }
    }
        generator = WatsonxGenerator(config)
        ctx = ("The quarter saw total revenue of $15bn, up one percent year-over-year (YoY). Software revenue increased "
               "by 10 percent YoY, while consulting revenue remained flat and infrastructure revenue fell by seven percent."
               "IBM's Infrastructure offerings saw revenues of $3bn in the quarter.")
        generated_response = generator.generate_stream(query="Describe IBM does revenue in Q3 2024", context=ctx)
        self.assertEqual(''.join(generated_response), " According to the given context, IBM's infrastructure "
                                                      "offerings saw revenues of $3bn in the quarter, indicating that"
                                                      " the revenue from this segment was $3 billion.")

    def test_invalid_generator_type(self):
        config = {'type': 'invalid'}
        with self.assertRaises(ValueError):
            WatsonxGenerator(config)

if __name__ == '__main__':
    unittest.main()