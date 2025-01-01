"""Tests for RuntimeConfigService."""

import pytest
from uuid import uuid4
from sqlalchemy.orm import Session

from rag_solution.services.runtime_config_service import RuntimeConfigService, RuntimeConfig
from rag_solution.models.provider_config import ProviderModelConfig
from rag_solution.schemas.provider_config_schema import ProviderModelConfigOutput
from rag_solution.models.user_provider_preference import UserProviderPreference
from rag_solution.models.llm_parameters import LLMParameters
from rag_solution.models.prompt_template import PromptTemplate
from core.custom_exceptions import ConfigurationError

@pytest.fixture
def runtime_config_service(db: Session):
    """Create RuntimeConfigService instance."""
    return RuntimeConfigService(db)

@pytest.fixture
def llm_parameters(db: Session):
    """Create test LLM parameters."""
    params = LLMParameters(
        name="test-params",
        max_new_tokens=100,
        temperature=0.7,
        top_k=50,
        top_p=1.0,
        is_default=True
    )
    db.add(params)
    db.commit()
    return params

@pytest.fixture
def prompt_template(db: Session):
    """Create test prompt template."""
    template = PromptTemplate(
        name="test-template",
        provider="test-provider",
        system_prompt="You are a helpful assistant",
        context_prefix="Context:",
        query_prefix="Question:",
        answer_prefix="Answer:",
        is_default=True
    )
    db.add(template)
    db.commit()
    return template

@pytest.fixture
def default_provider(db: Session, llm_parameters: LLMParameters):
    """Create default provider config."""
    config = ProviderModelConfig(
        model_id="default-model",
        provider_name="test-provider",
        api_key="default-key",
        default_model_id="default",
        parameters_id=llm_parameters.id,
        is_default=True,
        is_active=True
    )
    db.add(config)
    db.commit()
    return config

@pytest.fixture
def alternate_provider(db: Session, llm_parameters: LLMParameters):
    """Create alternate provider config."""
    config = ProviderModelConfig(
        model_id="alt-model",
        provider_name="test-provider",
        api_key="alt-key",
        default_model_id="alt",
        parameters_id=llm_parameters.id,
        is_default=False,
        is_active=True
    )
    db.add(config)
    db.commit()
    return config

def test_get_runtime_config_default(
    runtime_config_service: RuntimeConfigService,
    default_provider: ProviderModelConfig,
    llm_parameters: LLMParameters,
    prompt_template: PromptTemplate
):
    """Test getting runtime config with default provider."""
    config = runtime_config_service.get_runtime_config()
    
    assert isinstance(config, RuntimeConfig)
    assert isinstance(config.provider_config, ProviderModelConfigOutput)
    assert config.provider_config.id == default_provider.id
    assert config.llm_parameters.id == llm_parameters.id
    assert config.prompt_template.id == prompt_template.id

def test_get_runtime_config_user_preference(
    db: Session,
    runtime_config_service: RuntimeConfigService,
    default_provider: ProviderModelConfig,
    alternate_provider: ProviderModelConfig,
    llm_parameters: LLMParameters,
    prompt_template: PromptTemplate
):
    """Test getting runtime config with user preference."""
    # Create user preference
    user_id = uuid4()
    pref = UserProviderPreference(
        user_id=user_id,
        provider_config_id=alternate_provider.id
    )
    db.add(pref)
    db.commit()
    
    # Get config with user ID
    config = runtime_config_service.get_runtime_config(user_id)
    
    assert isinstance(config.provider_config, ProviderModelConfigOutput)
    assert config.provider_config.id == alternate_provider.id
    assert config.llm_parameters.id == llm_parameters.id
    assert config.prompt_template.id == prompt_template.id

def test_get_runtime_config_fallback(
    db: Session,
    runtime_config_service: RuntimeConfigService,
    default_provider: ProviderModelConfig,
    alternate_provider: ProviderModelConfig
):
    """Test fallback to first active provider."""
    # Remove default flag
    default_provider.is_default = False
    db.commit()
    
    config = runtime_config_service.get_runtime_config()
    assert isinstance(config.provider_config, ProviderModelConfigOutput)
    assert config.provider_config.id in {default_provider.id, alternate_provider.id}

def test_get_runtime_config_no_provider(
    db: Session,
    runtime_config_service: RuntimeConfigService
):
    """Test error when no provider available."""
    with pytest.raises(ConfigurationError, match="No valid provider configuration found"):
        runtime_config_service.get_runtime_config()

def test_get_runtime_config_inactive_provider(
    db: Session,
    runtime_config_service: RuntimeConfigService,
    default_provider: ProviderModelConfig
):
    """Test inactive provider is not selected."""
    default_provider.is_active = False
    db.commit()
    
    with pytest.raises(ConfigurationError, match="No valid provider configuration found"):
        runtime_config_service.get_runtime_config()

def test_set_user_provider_preference(
    runtime_config_service: RuntimeConfigService,
    default_provider: ProviderModelConfig
):
    """Test setting user provider preference."""
    user_id = uuid4()
    
    # Set preference
    pref = runtime_config_service.set_user_provider_preference(
        user_id,
        default_provider.id
    )
    
    assert pref.user_id == user_id
    assert pref.provider_config_id == default_provider.id
    
    # Get config should use preference
    config = runtime_config_service.get_runtime_config(user_id)
    assert isinstance(config.provider_config, ProviderModelConfigOutput)
    assert config.provider_config.id == default_provider.id

def test_set_user_provider_preference_invalid(
    runtime_config_service: RuntimeConfigService
):
    """Test error when setting invalid provider preference."""
    with pytest.raises(ConfigurationError, match="Provider config not found"):
        runtime_config_service.set_user_provider_preference(
            uuid4(),
            999  # Invalid provider ID
        )

def test_clear_user_provider_preference(
    db: Session,
    runtime_config_service: RuntimeConfigService,
    default_provider: ProviderModelConfig,
    alternate_provider: ProviderModelConfig
):
    """Test clearing user provider preference."""
    # Create user preference
    user_id = uuid4()
    pref = UserProviderPreference(
        user_id=user_id,
        provider_config_id=alternate_provider.id
    )
    db.add(pref)
    db.commit()
    
    # Verify preference exists
    config = runtime_config_service.get_runtime_config(user_id)
    assert config.provider_config.id == alternate_provider.id
    
    # Clear preference
    runtime_config_service.clear_user_provider_preference(user_id)
    
    # Verify falls back to default
    config = runtime_config_service.get_runtime_config(user_id)
    assert isinstance(config.provider_config, ProviderModelConfigOutput)
    assert config.provider_config.id == default_provider.id

def test_clear_nonexistent_preference(
    runtime_config_service: RuntimeConfigService
):
    """Test clearing preference that doesn't exist."""
    # Should not raise error
    runtime_config_service.clear_user_provider_preference(uuid4())

def test_get_runtime_config_missing_template(
    db: Session,
    runtime_config_service: RuntimeConfigService,
    default_provider: ProviderModelConfig
):
    """Test error when no template available."""
    with pytest.raises(ConfigurationError, match="No prompt template found"):
        runtime_config_service.get_runtime_config()

def test_get_runtime_config_missing_parameters(
    db: Session,
    runtime_config_service: RuntimeConfigService,
    default_provider: ProviderModelConfig,
    prompt_template: PromptTemplate
):
    """Test error when parameters not found."""
    # Delete parameters
    db.delete(default_provider.parameters)
    db.commit()
    
    with pytest.raises(ConfigurationError, match="LLM parameters not found"):
        runtime_config_service.get_runtime_config()

def test_multiple_instances(db: Session):
    """Test that multiple instances don't share state."""
    service1 = RuntimeConfigService(db)
    service2 = RuntimeConfigService(db)
    
    assert service1 is not service2
    assert service1.db is not service2.db
