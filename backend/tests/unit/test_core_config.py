"""Tests for core configuration settings."""

import pytest

from core.config import Settings


@pytest.mark.atomic
def test_settings_loaded_from_env(mock_settings):
    """Test that settings are loaded from environment variables."""
    # Test required settings
    assert mock_settings.jwt_secret_key == "test-secret-key"
    assert mock_settings.rag_llm == "watsonx"

    # Test WatsonX settings
    assert mock_settings.wx_api_key == "test-api-key"
    assert mock_settings.wx_url == "https://test.watsonx.ai"
    assert mock_settings.wx_project_id == "test-instance-id"  # This is aliased to WATSONX_INSTANCE_ID

    # Test default values
    assert mock_settings.vector_db == "milvus"
    assert mock_settings.milvus_host == "test-milvus-host"  # This comes from the environment variable
    assert mock_settings.project_name == "rag_modulo"


@pytest.mark.atomic
def test_settings_with_minimal_env(minimal_test_env):
    """Test that settings work with minimal environment variables."""
    # Create a fresh settings instance with minimal environment
    test_settings = Settings()

    # Test that default values are used when env vars are not set
    assert test_settings.vector_db == "milvus"  # Default value
    assert test_settings.milvus_host == "localhost"  # Default value
    assert test_settings.project_name == "rag_modulo"  # Default value

    # Test that required values are set
    assert test_settings.jwt_secret_key == "minimal-secret"
    assert test_settings.rag_llm == "watsonx"


@pytest.mark.atomic
def test_settings_isolation(isolated_test_env):
    """Test that settings work in completely isolated environment."""
    # This test should fail if settings require real environment variables
    with pytest.raises(ValueError):  # Should fail due to missing required env vars
        Settings()
