"""Tests for Generation Components."""

from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from rag_solution.generation.factories import GeneratorFactory
from rag_solution.generation.generator import AnthropicGenerator, OpenAIGenerator, WatsonxGenerator
from rag_solution.schemas.llm_parameters_schema import LLMParametersOutput
from rag_solution.schemas.llm_provider_schema import LLMProviderOutput
from rag_solution.services.llm_parameters_service import LLMParametersService
from rag_solution.services.llm_provider_service import LLMProviderService


@pytest.fixture
def db_session() -> Mock:
    """Create a mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def llm_provider_service(db_session: Mock) -> Mock:
    """Create a mock LLMProviderService instance."""
    return Mock(spec=LLMProviderService)


@pytest.fixture
def llm_parameters_service(db_session: Mock) -> Mock:
    """Create a mock LLMParametersService instance."""
    return Mock(spec=LLMParametersService)


@pytest.fixture
def sample_provider_output() -> LLMProviderOutput:
    """Create a sample provider output."""
    # Note: Assuming the LLMProviderOutput schema has been corrected to remove the api_key field.
    return LLMProviderOutput(
        id=uuid4(),
        name="watsonx",
        base_url="https://api.example.com",
        org_id="test-org",
        project_id="test-project",
        is_active=True,
        is_default=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_llm_parameters_output(sample_provider_output: LLMProviderOutput) -> LLMParametersOutput:
    """Create a sample LLM parameters output."""
    return LLMParametersOutput(
        id=uuid4(),
        user_id=sample_provider_output.id,  # Use the provider ID as user_id for testing
        name="Test Parameters",
        description="Test LLM parameters for generation tests",
        temperature=0.7,
        max_new_tokens=512,
        top_k=50,
        top_p=0.9,
        repetition_penalty=1.05,
        is_default=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.mark.integration
def test_generator_factory_watsonx() -> None:
    """Test creating a WatsonX generator."""
    config = {"type": "watsonx", "model_id": "test-model", "api_key": "test-key", "project_id": "test-project"}
    generator = GeneratorFactory.create_generator(config)
    assert isinstance(generator, WatsonxGenerator)


def test_generator_factory_openai() -> None:
    """Test creating an OpenAI generator."""
    config = {"type": "openai", "model_id": "test-model", "api_key": "test-key"}
    generator = GeneratorFactory.create_generator(config)
    assert isinstance(generator, OpenAIGenerator)


def test_generator_factory_anthropic() -> None:
    """Test creating an Anthropic generator."""
    config = {"type": "anthropic", "model_id": "test-model", "api_key": "test-key"}
    generator = GeneratorFactory.create_generator(config)
    assert isinstance(generator, AnthropicGenerator)


def test_generator_factory_invalid() -> None:
    """Test creating a generator with invalid type."""
    config = {"type": "invalid", "model_id": "test-model"}
    with pytest.raises(ValueError, match="Unsupported generator type: invalid"):
        GeneratorFactory.create_generator(config)


def test_generator_default_type() -> None:
    """Test creating a generator with default type (watsonx)."""
    config = {"model_id": "test-model", "api_key": "test-key", "project_id": "test-project"}
    generator = GeneratorFactory.create_generator(config)
    assert isinstance(generator, WatsonxGenerator)


if __name__ == "__main__":
    pytest.main([__file__])
