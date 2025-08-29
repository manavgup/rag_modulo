"""Tests for core configuration settings."""

from core.config import settings


def test_settings_loaded_from_env():
    """Test that settings are loaded from .env file."""
    # Test required settings
    assert settings.jwt_secret_key is not None
    assert settings.rag_llm is not None

    # Test WatsonX settings
    assert settings.wx_api_key is not None
    assert settings.wx_url is not None
    assert settings.wx_project_id is not None

    # Test default values
    assert settings.vector_db == "milvus"
    assert settings.milvus_host == "milvus-standalone"
    assert settings.project_name == "rag_modulo"
