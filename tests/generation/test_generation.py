"""Tests for Generation Components."""

import pytest
from unittest.mock import Mock
from sqlalchemy.orm import Session
from uuid import uuid4

from rag_solution.generation.factories import GeneratorFactory
from rag_solution.generation.generator import WatsonxGenerator, OpenAIGenerator, AnthropicGenerator
from rag_solution.services.llm_provider_service import LLMProviderService
from rag_solution.services.llm_parameters_service import LLMParametersService
from rag_solution.schemas.llm_parameters_schema import LLMParametersInput, LLMParametersOutput
from rag_solution.schemas.llm_provider_schema import LLMProviderOutput

@pytest.fixture
def db_session():
    """Create a mock database session."""
    return Mock(spec=Session)

@pytest.fixture
def llm_provider_service(db_session):
    """Create a mock LLMProviderService instance."""
    return Mock(spec=LLMProviderService)

@pytest.fixture
def llm_parameters_service(db_session):
    """Create a mock LLMParametersService instance."""
    return Mock(spec=LLMParametersService)

@pytest.fixture
def sample_provider_output():
    """Create a sample provider output."""
    return LLMProviderOutput(
        id=uuid4(),
        name="watsonx",
        base_url="https://api.example.com",
        api_key="test-api-key",
        project_id="test-project"
    )

@pytest.fixture
def sample_llm_parameters_input():
    """Create a sample LLM parameters input."""
    return LLMParametersInput(
        model_id="test-model",
        temperature=0.7,
        max_tokens=512,
        top_p=0.9,
        frequency_penalty=0.0,
        presence_penalty=0.0
    )

@pytest.fixture
def sample_llm_parameters_output(sample_llm_parameters_input):
    """Create a sample LLM parameters output."""
    return LLMParametersOutput(
        id=uuid4(),
        collection_id=uuid4(),
        model_id=sample_llm_parameters_input.model_id,
        temperature=sample_llm_parameters_input.temperature,
        max_tokens=sample_llm_parameters_input.max_tokens,
        top_p=sample_llm_parameters_input.top_p,
        frequency_penalty=sample_llm_parameters_input.frequency_penalty,
        presence_penalty=sample_llm_parameters_input.presence_penalty
    )

def test_generator_factory_watsonx():
    """Test creating a WatsonX generator."""
    config = {
        'type': 'watsonx',
        'model_id': 'test-model',
        'api_key': 'test-key',
        'project_id': 'test-project'
    }
    generator = GeneratorFactory.create_generator(config)
    assert isinstance(generator, WatsonxGenerator)

def test_generator_factory_openai():
    """Test creating an OpenAI generator."""
    config = {
        'type': 'openai',
        'model_id': 'test-model',
        'api_key': 'test-key'
    }
    generator = GeneratorFactory.create_generator(config)
    assert isinstance(generator, OpenAIGenerator)

def test_generator_factory_anthropic():
    """Test creating an Anthropic generator."""
    config = {
        'type': 'anthropic',
        'model_id': 'test-model',
        'api_key': 'test-key'
    }
    generator = GeneratorFactory.create_generator(config)
    assert isinstance(generator, AnthropicGenerator)

def test_generator_factory_invalid():
    """Test creating a generator with invalid type."""
    config = {
        'type': 'invalid',
        'model_id': 'test-model'
    }
    with pytest.raises(ValueError, match="Unsupported generator type: invalid"):
        GeneratorFactory.create_generator(config)

def test_generator_default_type():
    """Test creating a generator with default type (watsonx)."""
    config = {
        'model_id': 'test-model',
        'api_key': 'test-key',
        'project_id': 'test-project'
    }
    generator = GeneratorFactory.create_generator(config)
    assert isinstance(generator, WatsonxGenerator)

if __name__ == "__main__":
    pytest.main([__file__])
