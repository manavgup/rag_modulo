"""Tests for core configuration settings."""

import os
import sys
import pytest
from pydantic import ValidationError
from core.config import Settings, LegacySettings


@pytest.fixture(autouse=True)
def clean_env():
    """Clean environment variables and reload config module."""
    # Store original environment
    old_env = dict(os.environ)
    
    # Clear relevant env vars
    for key in list(os.environ.keys()):
        if key in [
            'JWT_SECRET_KEY', 'RAG_LLM', 'VECTOR_DB', 'MILVUS_HOST',
            'PROJECT_NAME', 'EMBEDDING_MODEL', 'CHUNKING_STRATEGY',
            'MAX_CHUNK_SIZE', 'USE_NEW_CONFIG'
        ]:
            del os.environ[key]
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(old_env)
    
    # Force reload of config module
    if 'core.config' in sys.modules:
        del sys.modules['core.config']


def test_settings_minimal_config():
    """Test minimal Settings configuration with required fields."""
    os.environ['JWT_SECRET_KEY'] = 'test_secret_key'
    
    settings = Settings()
    assert settings.jwt_secret_key == 'test_secret_key'
    assert settings.vector_db == 'milvus'
    assert settings.milvus_host == 'milvus-standalone'
    assert settings.project_name == 'rag_modulo'


def test_settings_custom_values():
    """Test Settings with custom environment values."""
    os.environ['JWT_SECRET_KEY'] = 'test_key'
    os.environ['VECTOR_DB'] = 'chromadb'
    os.environ['MILVUS_HOST'] = 'custom_host'
    os.environ['PROJECT_NAME'] = 'custom_project'

    settings = Settings()
    assert settings.vector_db == 'chromadb'
    assert settings.milvus_host == 'custom_host'
    assert settings.project_name == 'custom_project'


def test_legacy_settings_custom_values():
    """Test LegacySettings with custom environment values."""
    os.environ['RAG_LLM'] = 'test_llm'
    os.environ['EMBEDDING_MODEL'] = 'custom_model'
    os.environ['CHUNKING_STRATEGY'] = 'semantic'
    os.environ['MAX_CHUNK_SIZE'] = '600'

    settings = LegacySettings()
    assert settings.embedding_model == 'custom_model'
    assert settings.chunking_strategy == 'semantic'
    assert settings.max_chunk_size == 600