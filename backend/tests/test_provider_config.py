"""Tests for provider configuration models and schemas."""

import pytest
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from rag_solution.models.provider_config import ProviderModelConfig
from rag_solution.models.llm_parameters import LLMParameters
from rag_solution.models.user_provider_preference import UserProviderPreference
from rag_solution.schemas.provider_config_schema import (
    ProviderConfig,
    ProviderInDB,
    ProviderRuntimeSettings,
    ProviderUpdate
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
def runtime_config() -> ProviderRuntimeSettings:
    """Create test runtime configuration."""
    return ProviderRuntimeSettings(
        timeout=30,
        max_retries=3,
        batch_size=10,
        retry_delay=1.0,
        concurrency_limit=10,
        stream=False,
        rate_limit=10
    )

@pytest.fixture
def provider_config_input(runtime_config: ProviderRuntimeSettings) -> ProviderConfig:
    """Create test provider config input."""
    return ProviderConfig(
        model_id="test-model",
        provider_name="test-provider",
        api_key="test-key",
        default_model_id="default-model",
        embedding_model="test-embedding-model",
        runtime=runtime_config
    )

@pytest.fixture
def provider_config_service(db: Session) -> ProviderConfigService:
    """Create provider config service."""
    return ProviderConfigService(db)

def test_provider_config_schema_validation(runtime_config: ProviderRuntimeSettings):
    """Test provider config schema validation."""
    # Test valid input
    config = ProviderConfig(
        model_id="test-model",
        provider_name="test-provider",
        api_key="test-key",
        default_model_id="default-model",
        runtime=runtime_config
    )
    assert config.model_id == "test-model"
    assert config.provider_name == "test-provider"

    # Test invalid input
    with pytest.raises(ValueError):
        ProviderConfig(
            model_id="",  # Empty model_id
            provider_name="test-provider",
            api_key="test-key",
            default_model_id="default-model",
            runtime=runtime_config
        )

    with pytest.raises(ValueError):
        ProviderConfig(
            model_id="test-model",
            provider_name="test@provider",  # Invalid characters
            api_key="test-key",
            default_model_id="default-model",
            runtime=runtime_config
        )

def test_provider_config_creation(db: Session, llm_parameters):
    """Test creating a provider configuration."""
    config = ProviderModelConfig(
        model_id="test-model",
        provider_name="test-provider",
        api_key="test-key",
        default_model_id="default-model",
        parameters_id=llm_parameters.id,
        timeout=30,
        max_retries=3,
        batch_size=10,
        retry_delay=1.0,
        concurrency_limit=10,
        stream=False,
        rate_limit=10
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
        is_default=True,
        timeout=30,
        max_retries=3,
        batch_size=10,
        retry_delay=1.0,
        concurrency_limit=10,
        stream=False,
        rate_limit=10
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
        is_default=True,
        timeout=30,
        max_retries=3,
        batch_size=10,
        retry_delay=1.0,
        concurrency_limit=10,
        stream=False,
        rate_limit=10
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
            parameters_id=llm_parameters.id,
            timeout=30,
            max_retries=3,
            batch_size=10,
            retry_delay=1.0,
            concurrency_limit=10,
            stream=False,
            rate_limit=10
        )
    
    # Test empty provider_name
    with pytest.raises(ValueError):
        ProviderModelConfig(
            model_id="model",
            provider_name="",
            api_key="key",
            default_model_id="default",
            parameters_id=llm_parameters.id,
            timeout=30,
            max_retries=3,
            batch_size=10,
            retry_delay=1.0,
            concurrency_limit=10,
            stream=False,
            rate_limit=10
        )
    
    # Test empty api_key
    with pytest.raises(ValueError):
        ProviderModelConfig(
            model_id="model",
            provider_name="provider",
            api_key="",
            default_model_id="default",
            parameters_id=llm_parameters.id,
            timeout=30,
            max_retries=3,
            batch_size=10,
            retry_delay=1.0,
            concurrency_limit=10,
            stream=False,
            rate_limit=10
        )

def test_provider_config_relationships(db: Session, llm_parameters):
    """Test provider config relationships."""
    
    config = ProviderModelConfig(
        model_id="test-model",
        provider_name="test-provider",
        api_key="test-key",
        default_model_id="default-model",
        parameters_id=llm_parameters.id,
        timeout=30,
        max_retries=3,
        batch_size=10,
        retry_delay=1.0,
        concurrency_limit=10,
        stream=False,
        rate_limit=10
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

def test_schema_conversions(runtime_config: ProviderRuntimeSettings):
    """Test schema conversions between Input/InDB/Output types."""
    # Test Input to InDB conversion
    input_config = ProviderConfig(
        model_id="test-model",
        provider_name="test-provider",
        api_key="test-key",
        default_model_id="default-model",
        runtime=runtime_config
    )
    
    in_db = ProviderInDB(
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
    output = ProviderConfig.model_validate(in_db)
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
        parameters_id=llm_parameters.id,
        timeout=30,
        max_retries=3,
        batch_size=10,
        retry_delay=1.0,
        concurrency_limit=10,
        stream=False,
        rate_limit=10
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
    """Test provider config service CRUD operations with prompt template."""
    # Create prompt template
    from rag_solution.schemas.prompt_template_schema import PromptTemplateCreate
    template = PromptTemplateCreate(
        name="test-template",
        provider="test-provider",
        description="Test template",
        system_prompt="You are a helpful assistant",
        context_prefix="Context:",
        query_prefix="Question:",
        answer_prefix="Answer:",
        input_variables=["context", "question"],
        template_format="{question}",
        is_default=True
    )
    # Test creation with template
    created = provider_config_service.register_provider_model(
        provider="test-provider",
        model_id="test-model",
        parameters=llm_parameters,
        provider_config=provider_config_input,
        prompt_template=template
    )
    assert isinstance(created, ProviderConfig)
    assert created.model_id == provider_config_input.model_id
    assert created.provider_name == provider_config_input.provider_name

    # Test retrieval and verify template
    retrieved = provider_config_service.get_provider_config("test-provider")
    assert retrieved is not None
    assert isinstance(retrieved, ProviderConfig)
    assert retrieved.id == created.id

    # Verify template was created
    from rag_solution.repository.prompt_template_repository import PromptTemplateRepository
    template_repo = PromptTemplateRepository(db)
    saved_template = template_repo.get_default_for_provider("test-provider")
    assert saved_template is not None
    assert saved_template.template_format == "{question}"
    assert saved_template.input_variables == ["context", "question"]

    # Test update
    update_data = ProviderUpdate(
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

def test_provider_config_template_failures(
    db: Session,
    llm_parameters,
    provider_config_input,
    provider_config_service
):
    """Test provider config service template creation failures."""
    # Test template with invalid variables
    from rag_solution.schemas.prompt_template_schema import PromptTemplateCreate
    invalid_template = PromptTemplateCreate(
        name="invalid-template",
        provider="test-provider",
        description="Invalid template",
        system_prompt="You are a helpful assistant",
        context_prefix="Context:",
        query_prefix="Question:",
        answer_prefix="Answer:",
        input_variables=["context"],  # Missing 'question' variable
        template_format="{question}",  # Uses undeclared variable
        is_default=True
    )

    # Should raise error due to invalid template
    with pytest.raises(Exception) as exc_info:
        provider_config_service.register_provider_model(
            provider="test-provider",
            model_id="test-model",
            parameters=llm_parameters,
            provider_config=provider_config_input,
            prompt_template=invalid_template
        )
    assert "Template contains undeclared variables" in str(exc_info.value)

    # Test template without template_format
    minimal_template = PromptTemplateCreate(
        name="minimal-template",
        provider="test-provider",
        description="Minimal template",
        system_prompt="You are a helpful assistant",
        context_prefix="Context:",
        query_prefix="Question:",
        answer_prefix="Answer:",
        input_variables=[],
        template_format="",
        is_default=True
    )

    # Should succeed with minimal template
    created = provider_config_service.register_provider_model(
        provider="test-provider",
        model_id="test-model",
        parameters=llm_parameters,
        provider_config=provider_config_input,
        prompt_template=minimal_template
    )
    assert created is not None

    # Verify template was created
    from rag_solution.repository.prompt_template_repository import PromptTemplateRepository
    template_repo = PromptTemplateRepository(db)
    saved_template = template_repo.get_default_for_provider("test-provider")
    assert saved_template is not None
    assert saved_template.template_format == ""
    assert saved_template.input_variables == []

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
