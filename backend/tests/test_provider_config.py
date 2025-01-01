"""Tests for provider configuration models and schemas."""

import pytest
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from rag_solution.models.provider_config import ProviderModelConfig
from rag_solution.models.llm_parameters import LLMParameters
from rag_solution.models.user_provider_preference import UserProviderPreference
from rag_solution.schemas.provider_config_schema import (
    ProviderModelConfigInput,
    ProviderModelConfigInDB,
    ProviderModelConfigOutput,
    ProviderModelConfigUpdate
)
from rag_solution.services.provider_config_service import ProviderConfigService

@pytest.fixture
def llm_parameters(db: Session) -> LLMParameters:
    """Create test LLM parameters."""
    params = LLMParameters(
        name="test-params",
        max_new_tokens=100,
        temperature=0.7,
        top_k=50,
        top_p=1.0
    )
    db.add(params)
    db.commit()
    return params

@pytest.fixture
def provider_config_input() -> ProviderModelConfigInput:
    """Create test provider config input."""
    return ProviderModelConfigInput(
        model_id="test-model",
        provider_name="test-provider",
        api_key="test-key",
        default_model_id="default-model",
        embedding_model="test-embedding-model"
    )

@pytest.fixture
def provider_config_service(db: Session) -> ProviderConfigService:
    """Create provider config service."""
    return ProviderConfigService(db)

def test_provider_config_schema_validation():
    """Test provider config schema validation."""
    # Test valid input
    config = ProviderModelConfigInput(
        model_id="test-model",
        provider_name="test-provider",
        api_key="test-key",
        default_model_id="default-model"
    )
    assert config.model_id == "test-model"
    assert config.provider_name == "test-provider"

    # Test invalid input
    with pytest.raises(ValueError):
        ProviderModelConfigInput(
            model_id="",  # Empty model_id
            provider_name="test-provider",
            api_key="test-key",
            default_model_id="default-model"
        )

    with pytest.raises(ValueError):
        ProviderModelConfigInput(
            model_id="test-model",
            provider_name="test@provider",  # Invalid characters
            api_key="test-key",
            default_model_id="default-model"
        )

def test_provider_config_creation(db: Session, llm_parameters):
    """Test creating a provider configuration."""
    config = ProviderModelConfig(
        model_id="test-model",
        provider_name="test-provider",
        api_key="test-key",
        default_model_id="default-model",
        parameters_id=llm_parameters.id
    )
    db.add(config)
    db.commit()
    
    assert config.id is not None
    assert config.model_id == "test-model"
    assert config.provider_name == "test-provider"
    assert config.is_active is True
    assert config.is_default is False

def test_provider_config_default_flag(db: Session, llm_parameters):
    """Test that only one provider can be default."""
    
    # Create first provider as default
    config1 = ProviderModelConfig(
        model_id="model1",
        provider_name="provider1",
        api_key="key1",
        default_model_id="default1",
        parameters_id=llm_parameters.id,
        is_default=True
    )
    db.add(config1)
    db.commit()
    
    # Create second provider as default
    config2 = ProviderModelConfig(
        model_id="model2",
        provider_name="provider2",
        api_key="key2",
        default_model_id="default2",
        parameters_id=llm_parameters.id,
        is_default=True
    )
    db.add(config2)
    db.commit()
    
    # Refresh first config
    db.refresh(config1)
    
    # Check that first config is no longer default
    assert config1.is_default is False
    assert config2.is_default is True

def test_provider_config_validation(db: Session, llm_parameters):
    """Test provider config model validation."""
    
    # Test empty model_id
    with pytest.raises(ValueError):
        ProviderModelConfig(
            model_id="",
            provider_name="provider",
            api_key="key",
            default_model_id="default",
            parameters_id=llm_parameters.id
        )
    
    # Test empty provider_name
    with pytest.raises(ValueError):
        ProviderModelConfig(
            model_id="model",
            provider_name="",
            api_key="key",
            default_model_id="default",
            parameters_id=llm_parameters.id
        )
    
    # Test empty api_key
    with pytest.raises(ValueError):
        ProviderModelConfig(
            model_id="model",
            provider_name="provider",
            api_key="",
            default_model_id="default",
            parameters_id=llm_parameters.id
        )

def test_provider_config_relationships(db: Session, llm_parameters):
    """Test provider config relationships."""
    
    config = ProviderModelConfig(
        model_id="test-model",
        provider_name="test-provider",
        api_key="test-key",
        default_model_id="default-model",
            parameters_id=llm_parameters.id
    )
    db.add(config)
    db.commit()
    
    # Test parameters relationship
    assert config.parameters.id == llm_parameters.id
    assert config.parameters.name == "test-params"
    
    # Test cascade delete
    db.delete(llm_parameters)
    db.commit()
    
    # Config should be deleted
    assert db.query(ProviderModelConfig).filter_by(id=config.id).first() is None

def test_schema_conversions():
    """Test schema conversions between Input/InDB/Output types."""
    # Test Input to InDB conversion
    input_config = ProviderModelConfigInput(
        model_id="test-model",
        provider_name="test-provider",
        api_key="test-key",
        default_model_id="default-model"
    )
    
    in_db = ProviderModelConfigInDB(
        **input_config.model_dump(),
        id=1,
        parameters_id=1,
        last_verified=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    assert in_db.model_id == input_config.model_id
    assert in_db.provider_name == input_config.provider_name
    
    # Test InDB to Output conversion
    output = ProviderModelConfigOutput.model_validate(in_db)
    assert output.id == in_db.id
    assert output.model_id == in_db.model_id
    assert output.provider_name == in_db.provider_name

def test_user_provider_preference(db: Session, test_user, llm_parameters):
    """Test user provider preferences."""
    config = ProviderModelConfig(
        model_id="test-model",
        provider_name="test-provider",
        api_key="test-key",
        default_model_id="default-model",
        parameters_id=llm_parameters.id
    )
    db.add(config)
    db.commit()
    
    # Create preference
    pref = UserProviderPreference(
        user_id=test_user.id,
        provider_config_id=config.id
    )
    db.add(pref)
    db.commit()
    
    # Test relationships
    assert pref.provider_config.id == config.id
    
    # Test unique constraint
    with pytest.raises(IntegrityError):
        pref2 = UserProviderPreference(
            user_id=test_user.id,
            provider_config_id=config.id
        )
        db.add(pref2)
        db.commit()
    db.rollback()
    
    # Test cascade delete
    db.delete(config)
    db.commit()
    
    # Preference should be deleted
    assert db.query(UserProviderPreference).filter_by(id=pref.id).first() is None

def test_provider_config_service_crud(
    db: Session,
    llm_parameters,
    provider_config_input,
    provider_config_service
):
    """Test provider config service CRUD operations."""
    # Test creation
    created = provider_config_service.register_provider_model(
        provider="test-provider",
        model_id="test-model",
        parameters=llm_parameters,
        provider_config=provider_config_input
    )
    assert isinstance(created, ProviderModelConfigOutput)
    assert created.model_id == provider_config_input.model_id
    assert created.provider_name == provider_config_input.provider_name

    # Test retrieval
    retrieved = provider_config_service.get_provider_config("test-provider")
    assert retrieved is not None
    assert isinstance(retrieved, ProviderModelConfigOutput)
    assert retrieved.id == created.id

    # Test update
    update_data = ProviderModelConfigUpdate(
        embedding_model="updated-embedding-model"
    )
    updated = provider_config_service.update_provider_model(
        provider="test-provider",
        model_id="test-model",
        updates=update_data.model_dump(exclude_unset=True)
    )
    assert updated is not None
    assert updated.embedding_model == "updated-embedding-model"

    # Test deletion
    assert provider_config_service.delete_provider_model(
        provider="test-provider",
        model_id="test-model"
    ) is True

    # Verify deletion
    assert provider_config_service.get_provider_config("test-provider") is None

def test_provider_config_service_validation(
    db: Session,
    llm_parameters,
    provider_config_input,
    provider_config_service
):
    """Test provider config service validation."""
    # Test duplicate provider
    created = provider_config_service.register_provider_model(
        provider="test-provider",
        model_id="test-model",
        parameters=llm_parameters,
        provider_config=provider_config_input
    )
    assert created is not None

    # Attempt to create duplicate
    with pytest.raises(Exception):
        provider_config_service.register_provider_model(
            provider="test-provider",
            model_id="test-model",
            parameters=llm_parameters,
            provider_config=provider_config_input
        )

    # Test invalid provider name
    invalid_config = provider_config_input.model_copy()
    invalid_config.provider_name = "invalid@provider"
    with pytest.raises(ValueError):
        provider_config_service.register_provider_model(
            provider="invalid@provider",
            model_id="test-model",
            parameters=llm_parameters,
            provider_config=invalid_config
        )
