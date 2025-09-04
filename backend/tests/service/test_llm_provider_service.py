"""Tests for LLMProviderService with real database interactions."""

from uuid import uuid4

import pytest
from pydantic import SecretStr

from core.custom_exceptions import ProviderConfigError, ProviderValidationError
from rag_solution.schemas.llm_provider_schema import (
    LLMProviderInput,
    LLMProviderModelInput,
    LLMProviderModelOutput,
    LLMProviderOutput,
    ModelType,
)
from rag_solution.schemas.prompt_template_schema import PromptTemplateType
from rag_solution.services.llm_provider_service import LLMProviderService


@pytest.fixture
def provider_service(db_session):
    """Create a provider service instance."""
    return LLMProviderService(db_session)


@pytest.fixture
def sample_provider_input():
    """Create a sample provider input."""
    return LLMProviderInput(
        name="test-provider", base_url="https://api.test.com", api_key=SecretStr("test-key"), project_id="test-project"
    )


@pytest.fixture
def sample_model_input(sample_provider_input):
    """Create a sample model input."""
    return LLMProviderModelInput(
        provider_id=uuid4(),
        model_id="test-model",
        model_type=ModelType.GENERATION,
        is_default=True,
        max_tokens=1000,
        temperature=0.7,
    )


@pytest.mark.atomic
def test_create_provider(provider_service, sample_provider_input):
    """Test provider creation."""
    provider = provider_service.create_provider(sample_provider_input)

    assert isinstance(provider, LLMProviderOutput)
    assert provider.name == sample_provider_input.name
    assert provider.base_url == sample_provider_input.base_url
    assert provider.project_id == sample_provider_input.project_id
    assert provider.id is not None


def test_create_provider_validation_error(provider_service):
    """Test provider creation with invalid input."""
    invalid_input = LLMProviderInput(
        name="",  # Invalid empty name
        base_url="not-a-url",  # Invalid URL
        api_key=SecretStr("key"),
    )

    with pytest.raises(ProviderValidationError):
        provider_service.create_provider(invalid_input)


def test_get_provider_by_name(provider_service, sample_provider_input):
    """Test getting provider by name."""
    created = provider_service.create_provider(sample_provider_input)

    provider = provider_service.get_provider_by_name(sample_provider_input.name)
    assert provider is not None
    assert provider.id == created.id
    assert provider.name == created.name

    # Test case insensitive search
    provider = provider_service.get_provider_by_name(sample_provider_input.name.upper())
    assert provider is not None
    assert provider.id == created.id


def test_get_provider_by_id(provider_service, sample_provider_input):
    """Test getting provider by ID."""
    created = provider_service.create_provider(sample_provider_input)

    provider = provider_service.get_provider_by_id(created.id)
    assert provider is not None
    assert provider.id == created.id
    assert provider.name == created.name

    # Test nonexistent ID
    provider = provider_service.get_provider_by_id(uuid4())
    assert provider is None


def test_update_provider(provider_service, sample_provider_input):
    """Test provider update."""
    created = provider_service.create_provider(sample_provider_input)

    updates = {"name": "updated-name", "base_url": "https://updated.test.com", "api_key": SecretStr("new-key")}

    updated = provider_service.update_provider(created.id, updates)
    assert updated is not None
    assert updated.name == updates["name"]
    assert updated.base_url == updates["base_url"]


def test_delete_provider(provider_service, sample_provider_input):
    """Test provider deletion."""
    created = provider_service.create_provider(sample_provider_input)

    result = provider_service.delete_provider(created.id)
    assert result is True

    # Verify provider is deleted
    provider = provider_service.get_provider_by_id(created.id)
    assert provider is None


def test_create_provider_model(provider_service, sample_provider_input, sample_model_input):
    """Test model creation."""
    provider = provider_service.create_provider(sample_provider_input)
    sample_model_input.provider_id = provider.id

    model = provider_service.create_provider_model(sample_model_input)

    assert isinstance(model, LLMProviderModelOutput)
    assert model.provider_id == provider.id
    assert model.model_id == sample_model_input.model_id
    assert model.model_type == sample_model_input.model_type
    assert model.is_default == sample_model_input.is_default


def test_create_model_without_provider(provider_service, sample_model_input):
    """Test model creation without provider."""
    with pytest.raises(ProviderConfigError):
        provider_service.create_provider_model(sample_model_input)


def test_get_model_by_id(provider_service, sample_provider_input, sample_model_input):
    """Test getting model by ID."""
    provider = provider_service.create_provider(sample_provider_input)
    sample_model_input.provider_id = provider.id
    created = provider_service.create_provider_model(sample_model_input)

    model = provider_service.get_model_by_id(created.id)
    assert model is not None
    assert model.id == created.id
    assert model.model_id == created.model_id

    # Test nonexistent ID
    model = provider_service.get_model_by_id(uuid4())
    assert model is None


def test_update_model(provider_service, sample_provider_input, sample_model_input):
    """Test model update."""
    provider = provider_service.create_provider(sample_provider_input)
    sample_model_input.provider_id = provider.id
    created = provider_service.create_provider_model(sample_model_input)

    updates = {"model_id": "updated-model", "max_tokens": 2000, "temperature": 0.5}

    updated = provider_service.update_model(created.id, updates)
    assert updated is not None
    assert updated.model_id == updates["model_id"]
    assert updated.max_tokens == updates["max_tokens"]
    assert updated.temperature == updates["temperature"]


def test_delete_model(provider_service, sample_provider_input, sample_model_input):
    """Test model deletion."""
    provider = provider_service.create_provider(sample_provider_input)
    sample_model_input.provider_id = provider.id
    created = provider_service.create_provider_model(sample_model_input)

    result = provider_service.delete_model(created.id)
    assert result is True

    # Verify model is deleted
    model = provider_service.get_model_by_id(created.id)
    assert model is None


def test_get_provider_with_models(provider_service, sample_provider_input, sample_model_input):
    """Test getting provider with its models."""
    provider = provider_service.create_provider(sample_provider_input)
    sample_model_input.provider_id = provider.id
    model = provider_service.create_provider_model(sample_model_input)

    result = provider_service.get_provider_with_models(provider.id)
    assert result is not None
    assert "provider" in result
    assert "models" in result
    assert result["provider"].id == provider.id
    assert len(result["models"]) == 1
    assert result["models"][0].id == model.id


def test_convert_provider_data(provider_service):
    """Test provider data conversion."""
    data = {"name": "test", "api_key": SecretStr("secret-key"), "other_field": "value"}

    converted = provider_service._convert_provider_data(data)
    assert "api_key" in converted
    assert isinstance(converted["api_key"], str)
    assert converted["api_key"] == "secret-key"
    assert converted["other_field"] == data["other_field"]


def test_initialize_providers_creates_templates(provider_service, db_session, base_user):
    """Test that provider initialization creates default templates."""
    # Initialize providers
    providers = provider_service.initialize_providers()
    assert len(providers) > 0

    # Get templates for the first provider
    provider = providers[0]
    # Verify QUESTION_GENERATION template
    question_template = provider_service.prompt_template_service.get_by_type(
        PromptTemplateType.QUESTION_GENERATION, provider.id
    )
    assert question_template is not None
    assert question_template.template_type == PromptTemplateType.QUESTION_GENERATION
    assert question_template.is_default is True
    assert question_template.provider == provider.name

    # Verify RAG_QUERY template
    rag_template = provider_service.prompt_template_service.get_by_type(PromptTemplateType.RAG_QUERY, provider.id)
    assert rag_template is not None
    assert rag_template.template_type == PromptTemplateType.RAG_QUERY
    assert rag_template.is_default is True
    assert rag_template.provider == provider.name


def test_initialize_providers_updates_existing_templates(provider_service, db_session, base_user):
    """Test that provider initialization updates existing templates."""
    # First initialization
    providers = provider_service.initialize_providers()
    assert len(providers) > 0

    # Get initial template
    provider = providers[0]
    # Get initial templates
    initial_question_template = provider_service.prompt_template_service.get_by_type(
        PromptTemplateType.QUESTION_GENERATION, provider.id
    )
    initial_rag_template = provider_service.prompt_template_service.get_by_type(
        PromptTemplateType.RAG_QUERY, provider.id
    )
    assert initial_question_template is not None
    assert initial_rag_template is not None

    # Second initialization
    provider_service.initialize_providers()

    # Get updated templates
    updated_question_template = provider_service.prompt_template_service.get_by_type(
        PromptTemplateType.QUESTION_GENERATION, provider.id
    )
    updated_rag_template = provider_service.prompt_template_service.get_by_type(
        PromptTemplateType.RAG_QUERY, provider.id
    )

    # Verify templates were updated not duplicated
    assert updated_question_template.id == initial_question_template.id
    assert updated_rag_template.id == initial_rag_template.id


def test_get_user_provider_with_templates(provider_service, db_session, base_user):
    """Test getting user provider with associated templates."""
    # Get provider for user
    provider = provider_service.get_user_provider(base_user.id)
    assert provider is not None

    # Verify templates exist for this provider
    rag_template = provider_service.prompt_template_service.get_by_type(PromptTemplateType.RAG_QUERY, provider.id)
    question_template = provider_service.prompt_template_service.get_by_type(
        PromptTemplateType.QUESTION_GENERATION, provider.id
    )

    assert rag_template is not None
    assert question_template is not None
    assert rag_template.provider == provider.name
    assert question_template.provider == provider.name


def test_initialize_providers_template_error_handling(provider_service, db_session, base_user):
    """Test error handling during template initialization."""
    # First initialization should succeed
    providers = provider_service.initialize_providers(raise_on_error=False)
    assert len(providers) > 0
    provider = providers[0]

    # Delete templates to force re-creation
    db_session.execute("DELETE FROM prompt_templates")
    db_session.commit()

    # Second initialization with raise_on_error=False should not raise
    providers = provider_service.initialize_providers(raise_on_error=False)
    assert len(providers) > 0

    # Verify templates were recreated
    question_template = provider_service.prompt_template_service.get_by_type(
        PromptTemplateType.QUESTION_GENERATION, provider.id
    )
    rag_template = provider_service.prompt_template_service.get_by_type(PromptTemplateType.RAG_QUERY, provider.id)
    assert question_template is not None
    assert rag_template is not None


def test_get_provider_models(provider_service, db_session, base_user):
    """Test getting provider models."""
    # Get provider
    provider = provider_service.get_user_provider(base_user.id)
    assert provider is not None

    # Get models
    models = provider_service.get_models_by_provider(provider.id)
    assert len(models) > 0

    # Verify model types
    generation_models = [m for m in models if m.model_type == ModelType.GENERATION]
    embedding_models = [m for m in models if m.model_type == ModelType.EMBEDDING]

    assert len(generation_models) > 0
    assert len(embedding_models) > 0
    assert any(m.is_default for m in models)


if __name__ == "__main__":
    pytest.main([__file__])
