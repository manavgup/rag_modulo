"""Tests for core configuration settings."""

import os
from unittest.mock import patch

import pytest

from core.config import Settings


@pytest.mark.atomic
@patch.dict(
    os.environ,
    {
        "JWT_SECRET_KEY": "test-secret-key",
        "RAG_LLM": "watsonx",
        "WX_API_KEY": "test-api-key",
        "WX_URL": "https://test.watsonx.ai",
        "WX_PROJECT_ID": "test-project-id",
        "VECTOR_DB": "milvus",
        "MILVUS_HOST": "milvus-standalone",
        "PROJECT_NAME": "rag_modulo",
    },
)
def test_settings_loaded_from_env():
    """Test that settings are loaded from environment variables."""
    # Create a fresh settings instance with mocked environment
    test_settings = Settings()

    # Test required settings
    assert test_settings.jwt_secret_key == "test-secret-key"
    assert test_settings.rag_llm == "watsonx"

    # Test WatsonX settings
    assert test_settings.wx_api_key == "test-key"
    assert test_settings.wx_url == "https://test.watsonx.ai"
    assert test_settings.wx_project_id == "test-instance"  # This is aliased to WATSONX_INSTANCE_ID

    # Test default values
    assert test_settings.vector_db == "milvus"
    assert test_settings.milvus_host == "milvus-standalone"  # This comes from the environment variable
    assert test_settings.project_name == "rag_modulo"


@pytest.mark.atomic
@patch.dict(
    os.environ,
    {
        "JWT_SECRET_KEY": "minimal-secret",
        "RAG_LLM": "watsonx",
        "WATSONX_INSTANCE_ID": "minimal-instance",
        "WATSONX_APIKEY": "minimal-key",
        "WATSONX_URL": "https://minimal.watsonx.ai",
        "WATSONX_PROJECT_ID": "minimal-project",
    },
    clear=True,
)
def test_settings_with_minimal_env():
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
