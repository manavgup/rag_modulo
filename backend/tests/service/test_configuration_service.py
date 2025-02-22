"""Integration tests for configuration-related services."""

import pytest
from uuid import UUID
from typing import Dict, Any
from pydantic import SecretStr
from sqlalchemy.orm import Session

from rag_solution.services.llm_parameters_service import LLMParametersService
from rag_solution.services.prompt_template_service import PromptTemplateService
from rag_solution.services.llm_provider_service import LLMProviderService
from rag_solution.schemas.llm_provider_schema import (
    LLMProviderInput,
    LLMProviderOutput,
    LLMProviderModelInput,
    ModelType
)
from rag_solution.schemas.prompt_template_schema import PromptTemplateType, PromptTemplateInput
from rag_solution.schemas.llm_parameters_schema import LLMParametersInput
from core.custom_exceptions import (
    ProviderValidationError,
    ProviderConfigError,
    NotFoundException
)

@pytest.fixture
def test_provider_input() -> LLMProviderInput:
    """Create test provider input fixture."""
    return LLMProviderInput(
        name="test-watsonx",
        base_url="https://test.watsonx.ai/api",
        api_key=SecretStr("test-key"),
        project_id="test-project"
    )

@pytest.fixture
def test_model_input() -> LLMProviderModelInput:
    """Create test model input fixture."""
    return LLMProviderModelInput(
        provider_id=UUID("00000000-0000-0000-0000-000000000000"),  # Will be replaced in tests
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
        is_active=True
    )

@pytest.fixture
def test_llm_parameters(base_user) -> LLMParametersInput:
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
        is_default=True
    )

@pytest.fixture
def test_prompt_template(base_user) -> PromptTemplateInput:
    """Test prompt template data."""
    return PromptTemplateInput(
        name="test-template",
        provider="watsonx",
        template_type=PromptTemplateType.RAG_QUERY,
        system_prompt="You are a helpful AI assistant.",
        template_format="Context:\n{context}\nQuestion:{question}",
        input_variables={
            "context": "Retrieved context",
            "question": "User's question"
        },
        example_inputs={
            "context": "Initial context",
            "question": "Initial question"
        },
        is_default=True
    )

@pytest.mark.atomic
def test_create_provider(
    db_session: Session,
    test_provider_input: LLMProviderInput
):
    """Test creating LLM provider."""
    service = LLMProviderService(db_session)
    provider = service.create_provider(test_provider_input)
    
    assert isinstance(provider, LLMProviderOutput)
    assert provider.name == test_provider_input.name
    assert str(provider.base_url) == str(test_provider_input.base_url)
    assert provider.project_id == test_provider_input.project_id
    assert provider.is_active
    assert isinstance(provider.id, UUID)

@pytest.mark.atomic
def test_create_provider_model(
    db_session: Session,
    test_provider_input: LLMProviderInput,
    test_model_input: LLMProviderModelInput
):
    """Test creating provider model."""
    service = LLMProviderService(db_session)
    provider = service.create_provider(test_provider_input)
    test_model_input.provider_id = provider.id
    
    model = service.create_provider_model(test_model_input)
    assert model.model_id == test_model_input.model_id
    assert model.model_type == test_model_input.model_type
    assert model.is_default == test_model_input.is_default
    assert model.provider_id == provider.id

@pytest.mark.atomic
def test_create_llm_parameters(
    db_session: Session,
    test_llm_parameters: LLMParametersInput
):
    """Test creating LLM parameters."""
    service = LLMParametersService(db_session)
    params = service.create_parameters(test_llm_parameters.user_id, test_llm_parameters)
    
    assert params.name == test_llm_parameters.name
    assert params.user_id == test_llm_parameters.user_id
    assert params.max_new_tokens == test_llm_parameters.max_new_tokens
    assert params.temperature == test_llm_parameters.temperature
    assert params.is_default == test_llm_parameters.is_default

@pytest.mark.atomic
def test_create_prompt_template(
    db_session: Session,
    base_user,
    test_prompt_template: PromptTemplateInput
):
    """Test creating prompt template."""
    service = PromptTemplateService(db_session)
    template = service.create_or_update_template(base_user.id, test_prompt_template)
    
    assert template.name == test_prompt_template.name
    assert template.provider == test_prompt_template.provider
    assert template.template_type == test_prompt_template.template_type
    assert template.is_default == test_prompt_template.is_default

@pytest.mark.atomic
def test_configuration_flow(
    db_session: Session,
    base_user,
    test_provider_input: LLMProviderInput,
    test_model_input: LLMProviderModelInput,
    test_llm_parameters: LLMParametersInput,
    test_prompt_template: PromptTemplateInput
):
    """Test complete configuration flow."""
    provider_service = LLMProviderService(db_session)
    parameters_service = LLMParametersService(db_session)
    template_service = PromptTemplateService(db_session)
    
    # Create provider
    provider = provider_service.create_provider(test_provider_input)
    assert provider.id is not None
    
    # Create model
    test_model_input.provider_id = provider.id
    model = provider_service.create_provider_model(test_model_input)
    assert model.id is not None

    # Create LLM parameters
    params = parameters_service.create_parameters(base_user.id, test_llm_parameters)
    assert params.id is not None

    # Create prompt template
    template = template_service.create_or_update_template(base_user.id, test_prompt_template)
    assert template.id is not None

    # Verify relationships
    assert params.user_id == base_user.id
    assert template.user_id == base_user.id

@pytest.mark.atomic
def test_provider_validation_errors(db_session: Session):
    """Test provider validation error handling."""
    service = LLMProviderService(db_session)

    # Test invalid name
    with pytest.raises(ProviderValidationError) as exc_info:
        service.create_provider(LLMProviderInput(
            name="test@invalid",  # Invalid characters
            base_url="https://test.com",
            api_key=SecretStr("test-key"),
            project_id="test-project"
        ))
    assert "name" in str(exc_info.value)

    # Test invalid URL
    with pytest.raises(ProviderValidationError) as exc_info:
        service.create_provider(LLMProviderInput(
            name="test-provider",
            base_url="not-a-url",  # Invalid URL
            api_key=SecretStr("test-key"),
            project_id="test-project"
        ))
    assert "base_url" in str(exc_info.value)

@pytest.mark.atomic
def test_model_validation_errors(
    db_session: Session,
    test_provider_input: LLMProviderInput,
    test_model_input: LLMProviderModelInput
):
    """Test model validation error handling."""
    service = LLMProviderService(db_session)
    provider = service.create_provider(test_provider_input)
    test_model_input.provider_id = provider.id

    # Test invalid timeout
    invalid_model = test_model_input.model_copy(update={"timeout": 0})
    with pytest.raises(ProviderValidationError) as exc_info:
        service.create_provider_model(invalid_model)
    assert "timeout" in str(exc_info.value)

    # Test missing provider ID
    invalid_model = test_model_input.model_copy(update={"provider_id": None})
    with pytest.raises(ProviderConfigError) as exc_info:
        service.create_provider_model(invalid_model)
    assert "provider_id" in str(exc_info.value)

@pytest.mark.atomic
def test_not_found_errors(
    db_session: Session,
    base_user,
    test_llm_parameters: LLMParametersInput
):
    """Test not found error handling."""
    parameters_service = LLMParametersService(db_session)

    # Test non-existent user
    with pytest.raises(NotFoundException):
        parameters_service.create_parameters(
            UUID("00000000-0000-0000-0000-000000000000"),
            test_llm_parameters
        )

    # Test non-existent parameter ID
    with pytest.raises(NotFoundException):
        parameters_service.update_parameters(
            UUID("00000000-0000-0000-0000-000000000000"),
            test_llm_parameters
        )

if __name__ == "__main__":
    pytest.main([__file__])
