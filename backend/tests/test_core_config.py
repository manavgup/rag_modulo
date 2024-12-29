"""Tests for core configuration settings."""

import os
import pytest
from pydantic import ValidationError
from backend.core.config import Settings, LegacySettings

# Core Settings Tests
def test_minimal_config():
    """Test minimal configuration with only required settings."""
    os.environ['JWT_SECRET_KEY'] = 'test-key'
    settings = Settings()
    assert settings.jwt_secret_key == 'test-key'
    assert settings.jwt_algorithm == 'HS256'

def test_database_settings(mock_db_settings):
    """Test database configuration settings."""
    assert mock_db_settings.collectiondb_user == 'test_user'
    assert mock_db_settings.collectiondb_pass == 'test_pass'
    assert mock_db_settings.collectiondb_port == 5432

def test_watsonx_credentials(test_settings):
    """Test WatsonX credentials loading."""
    assert test_settings.wx_project_id == 'test-instance'
    assert test_settings.wx_api_key == 'test-api-key'
    assert test_settings.wx_url == 'https://test.watsonx.ai'

def test_invalid_port():
    """Test validation error for invalid port number."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(collectiondb_port=70000, jwt_secret_key='test-key')
    assert 'Port must be between 1 and 65535' in str(exc_info.value)

def test_missing_jwt_key():
    """Test error when required JWT key is missing."""
    if 'JWT_SECRET_KEY' in os.environ:
        del os.environ['JWT_SECRET_KEY']
    with pytest.raises(ValidationError) as exc_info:
        Settings()
    assert 'field required' in str(exc_info.value)
    assert 'jwt_secret_key' in str(exc_info.value)

def test_env_file_loading(tmp_path):
    """Test loading configuration from .env file."""
    env_file = tmp_path / ".env"
    env_file.write_text("""
    JWT_SECRET_KEY=file-test-key
    COLLECTIONDB_USER=file-test-user
    COLLECTIONDB_PORT=5555
    """)
    
    # Temporarily set env_file path
    Settings.Config.env_file = str(env_file)
    settings = Settings()
    
    assert settings.jwt_secret_key == 'file-test-key'
    assert settings.collectiondb_user == 'file-test-user'
    assert settings.collectiondb_port == 5555

# Legacy Settings Tests
def test_legacy_settings_compatibility():
    """Test that legacy settings maintain backward compatibility."""
    os.environ.update({
        'JWT_SECRET_KEY': 'test-key',
        'RAG_LLM': 'test-model',
        'CHUNKING_STRATEGY': 'test-strategy',
        'EMBEDDING_MODEL': 'test-embedding'
    })
    
    settings = LegacySettings()
    
    # Test core settings are still present
    assert settings.jwt_secret_key == 'test-key'
    assert settings.jwt_algorithm == 'HS256'
    
    # Test legacy settings
    assert settings.rag_llm == 'test-model'
    assert settings.chunking_strategy == 'test-strategy'
    assert settings.embedding_model == 'test-embedding'

def test_legacy_settings_defaults():
    """Test default values in legacy settings."""
    os.environ.update({
        'JWT_SECRET_KEY': 'test-key',
        'RAG_LLM': 'test-model'
    })
    
    settings = LegacySettings()
    
    # Test default values
    assert settings.chunk_overlap == 10
    assert settings.temperature == 0.7
    assert settings.max_new_tokens == 500

def test_feature_flag():
    """Test feature flag for configuration system."""
    os.environ.update({
        'JWT_SECRET_KEY': 'test-key',
        'RAG_LLM': 'test-model',
        'USE_NEW_CONFIG': 'true'
    })
    
    # When USE_NEW_CONFIG is true
    from backend.core.config import settings
    assert isinstance(settings, Settings)
    assert not isinstance(settings, LegacySettings)
    
    # When USE_NEW_CONFIG is false
    os.environ['USE_NEW_CONFIG'] = 'false'
    from importlib import reload
    import backend.core.config
    reload(backend.core.config)
    from backend.core.config import settings
    assert isinstance(settings, LegacySettings)

def test_legacy_settings_validation():
    """Test validation in legacy settings."""
    with pytest.raises(ValidationError) as exc_info:
        LegacySettings(
            jwt_secret_key='test-key',
            max_new_tokens=-1  # Invalid value
        )
    assert 'ensure this value is greater than or equal to 0' in str(exc_info.value)

def test_legacy_settings_override():
    """Test overriding default values in legacy settings."""
    custom_settings = LegacySettings(
        jwt_secret_key='test-key',
        RAG_LLM='custom-model',
        chunk_overlap=20,
        temperature=0.5,
        embedding_model='custom-embedding'
    )
    
    assert custom_settings.chunk_overlap == 20
    assert custom_settings.temperature == 0.5
    assert custom_settings.embedding_model == 'custom-embedding'

def test_env_var_parsing():
    """Test environment variable parsing for list fields."""
    os.environ.update({
        'JWT_SECRET_KEY': 'test-key',
        'RAG_LLM': 'test-model',
        'QUESTION_TYPES': '["What", "How", "Why"]'
    })
    
    settings = LegacySettings()
    assert settings.question_types == ['What', 'How', 'Why']
