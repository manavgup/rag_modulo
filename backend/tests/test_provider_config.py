"""Tests for provider configuration management."""

import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from core.custom_exceptions import LLMProviderError, ProviderConfigError
from rag_solution.models.provider_config import ProviderModelConfig
from rag_solution.schemas.provider_config_schema import (
    ProviderModelConfigBase,
    ProviderModelConfigCreate,
    ProviderModelConfigUpdate,
    ProviderModelConfigResponse
)
from rag_solution.repository.provider_config_repository import ProviderConfigRepository
from rag_solution.services.provider_config_service import ProviderConfigService
from rag_solution.schemas.llm_parameters_schema import LLMParametersCreate
from rag_solution.schemas.prompt_template_schema import PromptTemplateCreate
from rag_solution.generation.providers.watsonx import WatsonXProvider
from rag_solution.generation.providers.base import PROVIDER_ERROR_TYPES

@pytest.fixture
def provider_config_repo(db_session: Session) -> ProviderConfigRepository:
    """Fixture for provider config repository."""
    return ProviderConfigRepository(db_session)

@pytest.fixture
def provider_config_service(db_session: Session) -> ProviderConfigService:
    """Fixture for provider config service."""
    return ProviderConfigService(db_session)

@pytest.fixture
def sample_llm_params() -> LLMParametersCreate:
    """Fixture for sample LLM parameters."""
    return LLMParametersCreate(
        name="test_params",
        description="Test parameters",
        max_new_tokens=100,
        temperature=0.7,
        top_k=50,
        top_p=1.0
    )

@pytest.fixture
def sample_prompt_template() -> PromptTemplateCreate:
    """Fixture for sample prompt template."""
    return PromptTemplateCreate(
        name="test_template",
        provider="watsonx",
        description="Test template",
        system_prompt="You are a helpful AI assistant",
        context_prefix="Context:",
        query_prefix="Question:",
        answer_prefix="Answer:"
    )

@pytest.fixture
def sample_provider_base_config() -> ProviderModelConfigBase:
    """Fixture for sample provider base configuration."""
    return ProviderModelConfigBase(
        provider_name="watsonx",
        model_id="meta-llama/llama-3-1-8b-instruct",
        default_model_id="meta-llama/llama-3-1-8b-instruct",
        api_key="test-api-key",
        api_url="https://test.watsonx.ai/api",
        project_id="test-project",
        parameters_id=1,
        timeout=30,
        max_retries=3,
        batch_size=10
    )

@pytest.fixture
def sample_provider_config(
    db_session: Session,
    sample_llm_params: LLMParametersCreate
) -> ProviderModelConfig:
    """Fixture for sample provider configuration."""
    from rag_solution.repository.llm_parameters_repository import LLMParametersRepository
    
    # Create LLM parameters first
    params_repo = LLMParametersRepository(db_session)
    params = params_repo.create(sample_llm_params)
    
    # Create provider config
    config = ProviderModelConfig(
        provider_name="watsonx",
        model_id="meta-llama/llama-3-1-8b-instruct",
        default_model_id="meta-llama/llama-3-1-8b-instruct",
        api_key="test-api-key",
        api_url="https://test.watsonx.ai/api",
        project_id="test-project",
        parameters_id=params.id,
        timeout=30,
        max_retries=3,
        batch_size=10,
        is_active=True
    )
    db_session.add(config)
    db_session.commit()
    db_session.refresh(config)
    return config

def test_create_provider_config(
    provider_config_repo: ProviderConfigRepository,
    sample_provider_config: ProviderModelConfig
):
    """Test creating a provider configuration."""
    config = provider_config_repo.get(sample_provider_config.id)
    assert config is not None
    assert config.provider_name == "watsonx"
    assert config.model_id == "meta-llama/llama-3-1-8b-instruct"
    assert config.default_model_id == "meta-llama/llama-3-1-8b-instruct"
    assert config.api_key == "test-api-key"
    assert config.api_url == "https://test.watsonx.ai/api"
    assert config.project_id == "test-project"
    assert config.timeout == 30
    assert config.max_retries == 3
    assert config.batch_size == 10
    assert config.is_active is True

def test_get_provider_config_by_name(
    provider_config_service: ProviderConfigService,
    sample_provider_config: ProviderModelConfig
):
    """Test retrieving a provider configuration by name."""
    config = provider_config_service.get_provider_config("watsonx")
    assert config is not None
    assert config.provider_name == "watsonx"
    assert config.model_id == "meta-llama/llama-3-1-8b-instruct"
    assert config.default_model_id == "meta-llama/llama-3-1-8b-instruct"
    assert config.api_key == "test-api-key"
    assert config.api_url == "https://test.watsonx.ai/api"
    assert config.project_id == "test-project"

def test_get_provider_config_by_model(
    provider_config_repo: ProviderConfigRepository,
    sample_provider_config: ProviderModelConfig
):
    """Test retrieving a provider configuration by model."""
    config = provider_config_repo.get_by_provider_and_model(
        "watsonx",
        "meta-llama/llama-3-1-8b-instruct"
    )
    assert config is not None
    assert config.provider_name == "watsonx"
    assert config.model_id == "meta-llama/llama-3-1-8b-instruct"
    assert config.default_model_id == "meta-llama/llama-3-1-8b-instruct"

def test_list_provider_configs(
    provider_config_repo: ProviderConfigRepository,
    sample_provider_config: ProviderModelConfig
):
    """Test listing provider configurations."""
    result = provider_config_repo.list()
    assert result.total_providers >= 1
    assert result.active_providers >= 1
    assert len(result.providers) >= 1

def test_update_provider_config(
    provider_config_repo: ProviderConfigRepository,
    sample_provider_config: ProviderModelConfig
):
    """Test updating a provider configuration."""
    updates = ProviderModelConfigUpdate(
        is_active=False,
        timeout=60,
        max_retries=5
    )
    config = provider_config_repo.update(sample_provider_config.id, updates)
    assert config is not None
    assert config.is_active is False
    assert config.timeout == 60
    assert config.max_retries == 5

def test_delete_provider_config(
    provider_config_repo: ProviderConfigRepository,
    sample_provider_config: ProviderModelConfig
):
    """Test deleting a provider configuration."""
    result = provider_config_repo.delete(sample_provider_config.id)
    assert result is True
    config = provider_config_repo.get(sample_provider_config.id)
    assert config is None

def test_register_provider_model(
    provider_config_service: ProviderConfigService,
    sample_llm_params: LLMParametersCreate,
    sample_prompt_template: PromptTemplateCreate,
    sample_provider_base_config: ProviderModelConfigBase
):
    """Test registering a provider model through the service layer."""
    config = provider_config_service.register_provider_model(
        provider="watsonx",
        model_id="meta-llama/llama-3-1-8b-instruct",
        parameters=sample_llm_params,
        provider_config=sample_provider_base_config,
        prompt_template=sample_prompt_template
    )
    assert config is not None
    assert config.provider_name == "watsonx"
    assert config.model_id == "meta-llama/llama-3-1-8b-instruct"
    assert config.default_model_id == "meta-llama/llama-3-1-8b-instruct"
    assert config.api_key == "test-api-key"
    assert config.api_url == "https://test.watsonx.ai/api"
    assert config.project_id == "test-project"
    assert config.timeout == 30
    assert config.max_retries == 3
    assert config.batch_size == 10
    assert config.is_active is True

def test_register_duplicate_provider_model(
    provider_config_service: ProviderConfigService,
    sample_provider_config: ProviderModelConfig,
    sample_llm_params: LLMParametersCreate,
    sample_prompt_template: PromptTemplateCreate,
    sample_provider_base_config: ProviderModelConfigBase
):
    """Test attempting to register a duplicate provider model."""
    with pytest.raises(ProviderConfigError) as exc_info:
        provider_config_service.register_provider_model(
            provider="watsonx",
            model_id="meta-llama/llama-3-1-8b-instruct",
            parameters=sample_llm_params,
            provider_config=sample_provider_base_config,
            prompt_template=sample_prompt_template
        )
    assert exc_info.value.details["error_type"] == "duplicate_error"

def test_verify_provider_model(
    provider_config_service: ProviderConfigService,
    sample_provider_config: ProviderModelConfig
):
    """Test verifying a provider model."""
    config = provider_config_service.verify_provider_model(
        "watsonx",
        "meta-llama/llama-3-1-8b-instruct"
    )
    assert config is not None
    assert config.last_verified is not None

def test_deactivate_provider_model(
    provider_config_service: ProviderConfigService,
    sample_provider_config: ProviderModelConfig
):
    """Test deactivating a provider model."""
    config = provider_config_service.deactivate_provider_model(
        "watsonx",
        "meta-llama/llama-3-1-8b-instruct"
    )
    assert config is not None
    assert config.is_active is False

def test_provider_validation(db_session: Session):
    """Test provider-specific validation."""
    # Create provider config service with empty database
    provider_config_service = ProviderConfigService(db_session)
    
    # Test WatsonX provider with no config
    with pytest.raises(LLMProviderError) as exc_info:
        WatsonXProvider(provider_config_service)
    assert exc_info.value.details["error_type"] == PROVIDER_ERROR_TYPES["CONFIG_INVALID"]

def test_batch_size_validation():
    """Test batch size validation."""
    # Test invalid batch size
    with pytest.raises(ValueError):
        ProviderModelConfig(
            provider_name="watsonx",
            model_id="model",
            default_model_id="model",
            api_key="key",
            parameters_id=1,
            batch_size=0  # Invalid batch size
        )
    
    # Test valid batch size
    config = ProviderModelConfig(
        provider_name="watsonx",
        model_id="model",
        default_model_id="model",
        api_key="key",
        parameters_id=1,
        batch_size=5  # Valid batch size
    )
    assert config.batch_size == 5

def test_model_validation():
    """Test provider model configuration validation."""
    # Test invalid model_id
    with pytest.raises(ValueError):
        ProviderModelConfig(
            provider_name="watsonx",
            model_id="",  # Empty model_id
            default_model_id="model",
            api_key="key",
            parameters_id=1
        )
    
    # Test invalid provider_name
    with pytest.raises(ValueError):
        ProviderModelConfig(
            provider_name="",  # Empty provider_name
            model_id="meta-llama/llama-3-1-8b-instruct",
            default_model_id="model",
            api_key="key",
            parameters_id=1
        )
    
    # Test invalid timeout
    with pytest.raises(ValueError):
        ProviderModelConfig(
            provider_name="watsonx",
            model_id="model",
            default_model_id="model",
            api_key="key",
            parameters_id=1,
            timeout=0  # Invalid timeout
        )
    
    # Test invalid max_retries
    with pytest.raises(ValueError):
        ProviderModelConfig(
            provider_name="watsonx",
            model_id="model",
            default_model_id="model",
            api_key="key",
            parameters_id=1,
            max_retries=-1  # Invalid max_retries
        )

def test_schema_validation():
    """Test provider configuration schema validation."""
    # Test required fields
    with pytest.raises(ValueError):
        ProviderModelConfigCreate()
    
    # Test field constraints
    with pytest.raises(ValueError):
        ProviderModelConfigCreate(
            provider_name="",  # Empty provider_name
            model_id="meta-llama/llama-3-1-8b-instruct",
            default_model_id="model",
            api_key="key",
            parameters_id=1
        )
    
    # Test provider name format
    config = ProviderModelConfigCreate(
        provider_name="WatsonX",  # Mixed case
        model_id="model",
        default_model_id="model",
        api_key="key",
        parameters_id=1
    )
    assert config.provider_name == "watsonx"  # Should be converted to lowercase
    
    # Test runtime settings validation
    with pytest.raises(ValueError):
        ProviderModelConfigCreate(
            provider_name="watsonx",
            model_id="model",
            default_model_id="model",
            api_key="key",
            parameters_id=1,
            timeout=-1  # Invalid timeout
        )
