"""Tests for RuntimeConfigService."""

import pytest
from uuid import UUID
from sqlalchemy.orm import Session

from rag_solution.services.runtime_config_service import RuntimeConfigService, RuntimeServiceConfig
from rag_solution.models.provider_config import ProviderModelConfig
from rag_solution.services.provider_config_service import ProviderConfigService
from rag_solution.schemas.provider_config_schema import ProviderConfig
from rag_solution.models.user_provider_preference import UserProviderPreference
from core.custom_exceptions import ConfigurationError

@pytest.fixture
def runtime_config_service(db: Session):
    """Create RuntimeConfigService instance."""
    return RuntimeConfigService(db)

def test_get_runtime_config_default(
    runtime_config_service: RuntimeConfigService,
    default_provider: ProviderModelConfig,
):
    """Test getting default runtime configuration."""
    config = runtime_config_service.get_runtime_config()
    
    assert isinstance(config, RuntimeServiceConfig)
    assert isinstance(config.provider_config, ProviderConfig)
    assert config.provider_config.provider_name == default_provider.provider_name
    assert config.provider_config.model_id == default_provider.model_id

def test_get_runtime_config_user_preference(
    db: Session,
    runtime_config_service: RuntimeConfigService,
    default_provider: ProviderModelConfig,
):
    """Test getting runtime configuration with user preference."""
    # Create user preference
    user_id = UUID('12345678-1234-5678-1234-567812345678')
    preference = UserProviderPreference(
        user_id=user_id,
        provider_config_id=default_provider.id
    )
    db.add(preference)
    db.commit()

    config = runtime_config_service.get_runtime_config(user_id)
    assert isinstance(config, RuntimeServiceConfig)
    assert config.provider_config.id == default_provider.id

def test_get_runtime_config_no_providers(
    db: Session,
    runtime_config_service: RuntimeConfigService,
    default_provider: ProviderModelConfig,
):
    """Test error when no providers available."""
    # Deactivate all providers
    db.query(ProviderModelConfig).update({"is_active": False})
    db.commit()

    with pytest.raises(ConfigurationError) as exc:
        runtime_config_service.get_runtime_config()
    assert "No valid provider configuration found" in str(exc.value)

def test_get_runtime_config_no_template(
    runtime_config_service: RuntimeConfigService
):
    """Test error when no prompt template available."""
    with pytest.raises(ConfigurationError) as exc:
        runtime_config_service.get_runtime_config()
    assert "No prompt template found" in str(exc.value)

def test_set_user_provider_preference(
    runtime_config_service: RuntimeConfigService,
    default_provider: ProviderModelConfig
):
    """Test setting user provider preference."""
    user_id = UUID('12345678-1234-5678-1234-567812345678')
    
    preference = runtime_config_service.set_user_provider_preference(
        user_id=user_id,
        provider_config_id=default_provider.id
    )
    
    assert preference.user_id == user_id
    assert preference.provider_config_id == default_provider.id

def test_set_user_provider_preference_invalid(
    runtime_config_service: RuntimeConfigService
):
    """Test error when setting invalid provider preference."""
    user_id = UUID('12345678-1234-5678-1234-567812345678')
    invalid_id = 999999

    with pytest.raises(ConfigurationError) as exc:
        runtime_config_service.set_user_provider_preference(
            user_id=user_id,
            provider_config_id=invalid_id
        )
    assert "Provider config not found or inactive" in str(exc.value)

def test_clear_user_provider_preference(
    runtime_config_service: RuntimeConfigService,
    default_provider: ProviderModelConfig,
):
    """Test clearing user provider preference."""
    user_id = UUID('12345678-1234-5678-1234-567812345678')
    
    # First set a preference
    runtime_config_service.set_user_provider_preference(
        user_id=user_id,
        provider_config_id=default_provider.id
    )
    
    # Then clear it
    runtime_config_service.clear_user_provider_preference(user_id)
    
    # Verify it's cleared by getting default config
    config = runtime_config_service.get_runtime_config(user_id)
    assert config.provider_config.id == default_provider.id

def test_clear_nonexistent_preference(
    runtime_config_service: RuntimeConfigService
):
    """Test clearing nonexistent user preference."""
    user_id = UUID('12345678-1234-5678-1234-567812345678')
    
    # Should not raise any error
    runtime_config_service.clear_user_provider_preference(user_id)

def test_multiple_instances(
    db: Session,
    runtime_config_service: RuntimeConfigService,
    default_provider: ProviderModelConfig
):
    """Test that multiple instances don't share state."""
    service1 = RuntimeConfigService(db)
    config1 = service1.get_runtime_config()
    
    service2 = RuntimeConfigService(db)
    config2 = service2.get_runtime_config()
    
    assert isinstance(config1, RuntimeServiceConfig)
    assert isinstance(config2, RuntimeServiceConfig)
    assert config1.provider_config.id == config2.provider_config.id
