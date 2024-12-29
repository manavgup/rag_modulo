"""Tests for core configuration settings."""

import os
import pytest
from pydantic import ValidationError
from backend.core.config import Settings

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
