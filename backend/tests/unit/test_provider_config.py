"""Tests for LLM provider and parameter configuration."""

from uuid import UUID, uuid4

import pytest
from pydantic import SecretStr
from pydantic import ValidationError as PydanticValidationError

from core.custom_exceptions import LLMProviderError, ProviderConfigError, ProviderValidationError
from rag_solution.schemas.llm_provider_schema import (
    LLMProviderInput,
    LLMProviderModelInput,
    LLMProviderModelOutput,
    LLMProviderOutput,
    ModelType,
)
from rag_solution.services.llm_parameters_service import LLMParametersService
from rag_solution.services.llm_provider_service import LLMProviderService


@pytest.fixture
def provider_service(db_session):
    """Create provider service instance."""
    return LLMProviderService(db_session)


@pytest.fixture
def parameters_service(db_session):
    """Create parameters service instance."""
    return LLMParametersService(db_session)


@pytest.fixture
def valid_provider_input():
    """Create a valid provider input fixture."""
    return LLMProviderInput(
        name="test-watsonx",
        base_url="https://us-south.ml.cloud.ibm.com",
        api_key=SecretStr("test-key"),
        project_id="test-project",
    )


@pytest.fixture
def valid_model_input():
    """Create a valid model input fixture."""
    return LLMProviderModelInput(
        provider_id=uuid4(),
        model_id="google/flan-t5-large",
        default_model_id="google/flan-t5-large",
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


@pytest.mark.atomic
def test_create_provider(provider_service: LLMProviderService, valid_provider_input: LLMProviderInput):
    """
    Test creating a provider.

    Args:
        provider_service (LLMProviderService): The provider service instance.
        valid_provider_input (LLMProviderInput): The valid provider input fixture.
    """
    saved_provider = provider_service.create_provider(valid_provider_input)
    assert isinstance(saved_provider, LLMProviderOutput)
    assert saved_provider.name == "test-watsonx"
    assert str(saved_provider.base_url) == "https://us-south.ml.cloud.ibm.com"
    assert saved_provider.project_id == "test-project"
    assert saved_provider.is_active
    assert isinstance(saved_provider.id, UUID)


def test_create_provider_validation_error(provider_service: LLMProviderService):
    """
    Test provider creation with invalid data.

    Args:
        provider_service (LLMProviderService): The provider service instance.
    """
    with pytest.raises(ProviderValidationError) as exc_info:
        provider_service.create_provider(
            LLMProviderInput(
                name="test@invalid",  # Invalid characters
                base_url="https://test.com",
                api_key=SecretStr("test-key"),
            )
        )
    assert "name" in str(exc_info.value)
    assert "test@invalid" in str(exc_info.value)


def test_create_provider_model(
    provider_service: LLMProviderService,
    valid_provider_input: LLMProviderInput,
    valid_model_input: LLMProviderModelInput,
):
    """
    Test creating a provider with model.

    Args:
        provider_service (LLMProviderService): The provider service instance.
        valid_provider_input (LLMProviderInput): The valid provider input fixture.
        valid_model_input (LLMProviderModelInput): The valid model input fixture.
    """
    provider = provider_service.create_provider(valid_provider_input)
    valid_model_input.provider_id = provider.id

    model = provider_service.create_provider_model(valid_model_input)
    assert isinstance(model, LLMProviderModelOutput)
    assert model.model_id == "google/flan-t5-large"
    assert model.model_type == ModelType.GENERATION
    assert model.is_default
    assert model.provider_id == provider.id


def test_create_model_without_provider(provider_service: LLMProviderService, valid_model_input: LLMProviderModelInput):
    """
    Test creating model without provider ID.

    Args:
        provider_service (LLMProviderService): The provider service instance.
        valid_model_input (LLMProviderModelInput): The valid model input fixture.
    """
    valid_model_input.provider_id = None
    with pytest.raises(ProviderConfigError) as exc_info:
        provider_service.create_provider_model(valid_model_input)
    assert "provider_id is required" in str(exc_info.value)


def test_model_validation(valid_model_input: LLMProviderModelInput):
    """
    Test model configuration validation.

    Args:
        valid_model_input (LLMProviderModelInput): The valid model input fixture.
    """
    # Test timeout bounds
    with pytest.raises(PydanticValidationError):
        valid_model_input.timeout = 0
    with pytest.raises(PydanticValidationError):
        valid_model_input.timeout = 301

    # Test retry bounds
    with pytest.raises(PydanticValidationError):
        valid_model_input.max_retries = -1
    with pytest.raises(PydanticValidationError):
        valid_model_input.max_retries = 11

    # Test batch size bounds
    with pytest.raises(PydanticValidationError):
        valid_model_input.batch_size = 0
    with pytest.raises(PydanticValidationError):
        valid_model_input.batch_size = 101

    # Test retry delay bounds
    with pytest.raises(PydanticValidationError):
        valid_model_input.retry_delay = 0.0
    with pytest.raises(PydanticValidationError):
        valid_model_input.retry_delay = 60.1


def test_get_provider(provider_service: LLMProviderService, valid_provider_input: LLMProviderInput):
    """
    Test retrieving a provider.

    Args:
        provider_service (LLMProviderService): The provider service instance.
        valid_provider_input (LLMProviderInput): The valid provider input fixture.
    """
    saved_provider = provider_service.create_provider(valid_provider_input)
    retrieved = provider_service.get_provider_by_id(saved_provider.id)

    assert retrieved is not None
    assert isinstance(retrieved, LLMProviderOutput)
    assert retrieved.name == "test-watsonx"
    assert str(retrieved.base_url) == "https://us-south.ml.cloud.ibm.com"


def test_get_nonexistent_provider(provider_service: LLMProviderService):
    """
    Test retrieving a non-existent provider.

    Args:
        provider_service (LLMProviderService): The provider service instance.
    """
    retrieved = provider_service.get_provider_by_id(uuid4())
    assert retrieved is None


def test_update_provider(provider_service: LLMProviderService, valid_provider_input: LLMProviderInput):
    """
    Test updating a provider.

    Args:
        provider_service (LLMProviderService): The provider service instance.
        valid_provider_input (LLMProviderInput): The valid provider input fixture.
    """
    saved_provider = provider_service.create_provider(valid_provider_input)

    # Update provider
    updates = {"is_active": False}
    updated = provider_service.update_provider(saved_provider.id, updates)

    assert isinstance(updated, LLMProviderOutput)
    assert not updated.is_active
    assert updated.name == saved_provider.name


def test_update_provider_validation_error(provider_service: LLMProviderService, valid_provider_input: LLMProviderInput):
    """
    Test provider update with invalid data.

    Args:
        provider_service (LLMProviderService): The provider service instance.
        valid_provider_input (LLMProviderInput): The valid provider input fixture.
    """
    saved_provider = provider_service.create_provider(valid_provider_input)

    with pytest.raises(ProviderValidationError) as exc_info:
        provider_service.update_provider(
            saved_provider.id,
            {
                "base_url": "not-a-url"  # Invalid URL
            },
        )
    assert "base_url" in str(exc_info.value)
    assert "not-a-url" in str(exc_info.value)


def test_delete_provider(provider_service: LLMProviderService, valid_provider_input: LLMProviderInput):
    """
    Test deleting a provider.

    Args:
        provider_service (LLMProviderService): The provider service instance.
        valid_provider_input (LLMProviderInput): The valid provider input fixture.
    """
    saved_provider = provider_service.create_provider(valid_provider_input)
    assert provider_service.delete_provider(saved_provider.id)

    retrieved = provider_service.get_provider_by_id(saved_provider.id)
    assert retrieved is None


def test_get_active_providers(provider_service: LLMProviderService):
    """
    Test retrieving all active providers.

    Args:
        provider_service (LLMProviderService): The provider service instance.
    """
    # Create multiple providers
    providers = []
    for i in range(3):
        provider_input = LLMProviderInput(
            name=f"test-provider-{i}", base_url="https://test.com", api_key=SecretStr("test-key")
        )
        provider = provider_service.create_provider(provider_input)
        if i == 2:  # Make last one inactive
            provider_service.update_provider(provider.id, {"is_active": False})
        providers.append(provider)

    active_providers = provider_service.get_all_providers(is_active=True)
    assert len(active_providers) == 2
    assert all(isinstance(p, LLMProviderOutput) for p in active_providers)
    assert all(p.is_active for p in active_providers)


def test_provider_with_models(
    provider_service: LLMProviderService,
    valid_provider_input: LLMProviderInput,
    valid_model_input: LLMProviderModelInput,
):
    """
    Test retrieving provider with models.

    Args:
        provider_service (LLMProviderService): The provider service instance.
        valid_provider_input (LLMProviderInput): The valid provider input fixture.
        valid_model_input (LLMProviderModelInput): The valid model input fixture.
    """
    provider = provider_service.create_provider(valid_provider_input)
    valid_model_input.provider_id = provider.id
    model = provider_service.create_provider_model(valid_model_input)

    result = provider_service.get_provider_with_models(provider.id)
    assert result is not None
    assert isinstance(result["provider"], LLMProviderOutput)
    assert len(result["models"]) == 1
    assert isinstance(result["models"][0], LLMProviderModelOutput)
    assert result["models"][0].id == model.id


def test_provider_initialization(provider_service: LLMProviderService, monkeypatch):
    """
    Test provider initialization with environment variables.

    Args:
        provider_service (LLMProviderService): The provider service instance.
        monkeypatch: The monkeypatch fixture for mocking environment variables.
    """
    # Mock environment variables
    monkeypatch.setattr("core.config.settings.wx_api_key", "test-key")
    monkeypatch.setattr("core.config.settings.wx_project_id", "test-project")

    providers = provider_service.initialize_providers(raise_on_error=True)
    assert len(providers) == 1
    assert providers[0].name == "watsonx"
    assert isinstance(providers[0], LLMProviderOutput)


def test_provider_initialization_error(provider_service: LLMProviderService, monkeypatch):
    """
    Test provider initialization with invalid data.

    Args:
        provider_service (LLMProviderService): The provider service instance.
        monkeypatch: The monkeypatch fixture for mocking environment variables.
    """
    # Mock environment variables with invalid data
    monkeypatch.setattr("core.config.settings.wx_api_key", "test-key")
    monkeypatch.setattr("core.config.settings.wx_project_id", "test-project")
    monkeypatch.setattr("core.config.settings.wx_url", "not-a-url")

    with pytest.raises(LLMProviderError) as exc_info:
        provider_service.initialize_providers(raise_on_error=True)
    assert "initialization" in str(exc_info.value)
    assert "watsonx" in str(exc_info.value)
