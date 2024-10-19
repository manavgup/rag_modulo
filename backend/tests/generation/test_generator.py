import pytest
from unittest.mock import patch, MagicMock
from rag_solution.generation.generator import WatsonxGenerator, OpenAIGenerator, AnthropicGenerator, PromptTemplate

@pytest.fixture
def sample_config():
    return {
        'type': 'watsonx',
        'model_name': 'flan-t5-xl',
        'default_params': {
            'max_new_tokens': 100,
            'temperature': 0.7
        }
    }

@pytest.fixture
def sample_documents():
    return [{"content": "Einstein's theory of relativity deals with space and time."}]

@pytest.fixture
def sample_query():
    return "Explain the theory of relativity in simple terms."

@pytest.fixture
def mock_prompt_config():
    return {
        "watsonx": {
            "system_prompt": "You are an AI assistant specializing in answering questions based on the given context.",
            "context_prefix": "Context:",
            "query_prefix": "Question:",
            "answer_prefix": "Answer:"
        },
        "openai": {
            "system_prompt": "You are a helpful AI assistant. Your task is to answer questions based on the provided context.",
            "context_prefix": "Here's some relevant information:",
            "query_prefix": "Please answer the following question:",
            "answer_prefix": "Response:"
        },
        "anthropic": {
            "system_prompt": "You are Claude, an AI assistant created by Anthropic to be helpful, harmless, and honest. Your goal is to provide accurate and helpful answers based on the given context.",
            "context_prefix": "Relevant information:",
            "query_prefix": "Human question:",
            "answer_prefix": "Claude's response:"
        }
    }

@patch('rag_solution.generation.generator.open')
def test_prompt_template_loading(mock_open, mock_prompt_config, sample_config):
    mock_open.return_value.__enter__.return_value.read.return_value = str(mock_prompt_config)
    generator = WatsonxGenerator(sample_config)
    assert isinstance(generator.prompt_template, PromptTemplate)
    assert generator.prompt_template.system_prompt == mock_prompt_config['watsonx']['system_prompt']

@patch('rag_solution.generation.generator.generate_text')
def test_watsonx_generator(mock_generate_text, sample_config, sample_query, sample_documents):
    mock_generate_text.return_value = "Simplified explanation of relativity."
    generator = WatsonxGenerator(sample_config)
    result = generator.generate(sample_query, sample_documents)
    assert result == "Simplified explanation of relativity."
    mock_generate_text.assert_called_once()

@patch('rag_solution.generation.generator.openai.ChatCompletion.create')
def test_openai_generator(mock_create, sample_config, sample_query, sample_documents):
    sample_config['type'] = 'openai'
    mock_response = MagicMock()
    mock_response.choices[0].message['content'] = "OpenAI explanation of relativity."
    mock_create.return_value = mock_response
    generator = OpenAIGenerator(sample_config)
    result = generator.generate(sample_query, sample_documents)
    assert result == "OpenAI explanation of relativity."
    mock_create.assert_called_once()

@patch('rag_solution.generation.generator.anthropic.Anthropic')
def test_anthropic_generator(mock_anthropic, sample_config, sample_query, sample_documents):
    sample_config['type'] = 'anthropic'
    mock_client = MagicMock()
    mock_client.completions.create.return_value.completion = "Anthropic explanation of relativity."
    mock_anthropic.return_value = mock_client
    generator = AnthropicGenerator(sample_config)
    result = generator.generate(sample_query, sample_documents)
    assert result == "Anthropic explanation of relativity."
    mock_client.completions.create.assert_called_once()

@patch('rag_solution.generation.generator.generate_text_stream')
def test_watsonx_generator_stream(mock_generate_text_stream, sample_config, sample_query, sample_documents):
    mock_generate_text_stream.return_value = iter(["Simplified ", "explanation ", "of relativity."])
    generator = WatsonxGenerator(sample_config)
    result = list(generator.generate_stream(sample_query, sample_documents))
    assert result == ["Simplified ", "explanation ", "of relativity."]
    mock_generate_text_stream.assert_called_once()

if __name__ == "__main__":
    pytest.main()