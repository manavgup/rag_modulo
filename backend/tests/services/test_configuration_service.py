"""Integration tests for configuration-related services."""

from typing import Any

import pytest
from pydantic import UUID4, SecretStr

from core.custom_exceptions import NotFoundException, ProviderConfigError, ProviderValidationError, RepositoryError
from rag_solution.schemas.llm_model_schema import LLMModelInput, ModelType
from rag_solution.schemas.llm_parameters_schema import LLMParametersInput
from rag_solution.schemas.llm_provider_schema import LLMProviderInput, LLMProviderOutput
from rag_solution.schemas.prompt_template_schema import PromptTemplateInput, PromptTemplateType


# -------------------------------------------
# 🔧 Provider Test Fixtures
# -------------------------------------------
@pytest.fixture
def test_provider_input() -> LLMProviderInput:
    """Create test provider input fixture."""
    return LLMProviderInput(
        name="test-watsonx",
        base_url="https://test.watsonx.ai/api",
        api_key=SecretStr("test-key"),
        project_id="test-project",
        org_id="test-org",
        is_active=True,
        is_default=False,
        user_id=UUID4("00000000-0000-0000-0000-000000000001"),
    )


@pytest.fixture
def test_model_input() -> LLMModelInput:
    """Create test model input fixture."""
    return LLMModelInput(
        provider_id=UUID4("00000000-0000-0000-0000-000000000000"),  # Will be replaced in tests
        model_id="granite-13b",
        default_model_id="granite-13b",
        model_type=ModelType.GENERATION,
        timeout=30,
        max_retries=3,
        batch_size=10,
        retry_delay=1.0,
        concurrency_limit=10,
        stream=False,
        rate_limit=10,
        is_default=True,
        is_active=True,
    )


@pytest.fixture
def test_llm_parameters(base_user: Any) -> LLMParametersInput:
    """Test LLM parameters data."""
    return LLMParametersInput(
        name="test-params",
        user_id=base_user.id,
        description="Test parameters",
        max_new_tokens=1000,
        temperature=0.7,
        top_k=50,
        top_p=1.0,
        repetition_penalty=1.1,
        is_default=True,
    )


@pytest.fixture
def test_prompt_template(base_user: Any) -> PromptTemplateInput:
    """Test prompt template data."""
    return PromptTemplateInput(
        name="test-template",
        user_id=base_user.id,
        template_type=PromptTemplateType.RAG_QUERY,
        system_prompt="You are a helpful AI assistant.",
        template_format="Context:\n{context}\nQuestion:{question}",
        input_variables={"context": "Retrieved context", "question": "User's question"},
        example_inputs={"context": "Initial context", "question": "Initial question"},
        max_context_length=1000,
        is_default=True,
    )


# -------------------------------------------
# 🧪 Provider Tests
# -------------------------------------------
def test_create_provider(llm_provider_service: Any, test_provider_input: LLMProviderInput) -> None:
    """Test creating LLM provider."""
    provider = llm_provider_service.create_provider(test_provider_input)

    assert isinstance(provider, LLMProviderOutput)
    assert provider.name == test_provider_input.name
    assert str(provider.base_url) == str(test_provider_input.base_url)
    assert provider.project_id == test_provider_input.project_id
    assert provider.is_active
    assert isinstance(provider.id, UUID4)


def test_create_provider_model(
    llm_provider_service: Any,
    llm_model_service: Any,
    test_provider_input: LLMProviderInput,
    test_model_input: LLMModelInput,
) -> None:
    """Test creating provider model."""
    provider = llm_provider_service.create_provider(test_provider_input)
    test_model_input.provider_id = provider.id

    model = llm_model_service.create_model(test_model_input)
    assert model.model_id == test_model_input.model_id
    assert model.model_type == test_model_input.model_type
    assert model.is_default == test_model_input.is_default
    assert model.provider_id == provider.id


# -------------------------------------------
# 🧪 LLM Parameters Tests
# -------------------------------------------
def test_create_llm_parameters(llm_parameters_service: Any, test_llm_parameters: LLMParametersInput, base_user: Any) -> None:
    """Test creating LLM parameters."""
    params = llm_parameters_service.create_parameters(base_user.id, test_llm_parameters)

    assert params.name == test_llm_parameters.name
    assert params.user_id == base_user.id
    assert params.max_new_tokens == test_llm_parameters.max_new_tokens
    assert params.temperature == test_llm_parameters.temperature
    assert params.is_default == test_llm_parameters.is_default


# -------------------------------------------
# 🧪 Prompt Template Tests
# -------------------------------------------
def test_create_prompt_template(prompt_template_service: Any, base_user: Any, test_prompt_template: Any) -> None:
    """Test creating prompt template."""
    template = prompt_template_service.create_or_update_template(base_user.id, test_prompt_template)

    assert template.name == test_prompt_template.name
    assert template.template_type == test_prompt_template.template_type
    assert template.is_default == test_prompt_template.is_default


# -------------------------------------------
# 🧪 Integration Tests
# -------------------------------------------
def test_configuration_flow(
    llm_provider_service: Any,
    llm_parameters_service: Any,
    prompt_template_service: Any,
    base_user: Any,
    test_provider_input: Any,
    test_model_input: Any,
    test_llm_parameters: Any,
    test_prompt_template: Any,
) -> None:
    """Test complete configuration flow."""
    # Create provider
    provider = llm_provider_service.create_provider(test_provider_input)
    assert provider.id is not None

    # Create model
    test_model_input.provider_id = provider.id
    model = llm_provider_service.create_provider_model(test_model_input)
    assert model.id is not None

    # Create LLM parameters
    params = llm_parameters_service.create_parameters(base_user.id, test_llm_parameters)
    assert params.id is not None

    # Create prompt template
    template = prompt_template_service.create_or_update_template(base_user.id, test_prompt_template)
    assert template.id is not None

    # Verify relationships
    assert params.user_id == base_user.id
    assert template.user_id == base_user.id


# -------------------------------------------
# 🧪 Error Tests
# -------------------------------------------
def test_provider_validation_errors(llm_provider_service: Any) -> None:
    """Test provider validation error handling."""
    # Test invalid name
    with pytest.raises(ProviderValidationError) as exc_info:
        llm_provider_service.create_provider(
            LLMProviderInput(
                name="test@invalid",  # Invalid characters
                base_url="https://test.com",
                api_key=SecretStr("test-key"),
                project_id="test-project",
                org_id="test-org",
                is_active=True,
                is_default=False,
                user_id=UUID4("00000000-0000-0000-0000-000000000001"),
            )
        )
    assert "name" in str(exc_info.value)

    # Test invalid URL
    with pytest.raises(ProviderValidationError) as exc_info:
        llm_provider_service.create_provider(
            LLMProviderInput(
                name="test-provider",
                base_url="not-a-url",  # Invalid URL
                api_key=SecretStr("test-key"),
                project_id="test-project",
                org_id="test-org",
                is_active=True,
                is_default=False,
                user_id=UUID4("00000000-0000-0000-0000-000000000001"),
            )
        )
    assert "base_url" in str(exc_info.value)


def test_model_validation_errors(llm_provider_service: Any, test_provider_input: LLMProviderInput, test_model_input: LLMModelInput) -> None:
    """Test model validation error handling."""
    # Create provider first
    provider = llm_provider_service.create_provider(test_provider_input)
    test_model_input.provider_id = provider.id

    # Test invalid timeout
    invalid_model = test_model_input.model_copy(update={"timeout": 0})
    with pytest.raises(ProviderValidationError) as exc_info:
        llm_provider_service.create_provider_model(invalid_model)
    assert "timeout" in str(exc_info.value)

    # Test missing provider ID
    invalid_model = test_model_input.model_copy(update={"provider_id": None})
    with pytest.raises(ProviderConfigError) as exc_info2:
        llm_provider_service.create_provider_model(invalid_model)
    assert "provider_id" in str(exc_info2.value)


def test_not_found_errors(llm_parameters_service: Any, base_user: Any, test_llm_parameters: Any) -> None:
    """Test not found error handling."""
    # Test non-existent user
    with pytest.raises(RepositoryError) as exc_info:
        llm_parameters_service.create_parameters(UUID4("00000000-0000-0000-0000-000000000000"), test_llm_parameters)
    assert "Referenced user" in str(exc_info.value.message)
    assert exc_info.value.details["constraint"] == "foreign_key"

    # Test non-existent parameter ID
    with pytest.raises(NotFoundException):
        llm_parameters_service.update_parameters(UUID4("00000000-0000-0000-0000-000000000000"), test_llm_parameters)


if __name__ == "__main__":
    pytest.main([__file__])
