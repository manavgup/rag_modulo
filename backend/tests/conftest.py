"""Pytest configuration and shared fixtures."""

import os
import pytest


@pytest.fixture(autouse=True)
def env_cleanup():
    """Cleanup environment variables after each test."""
    # Store original environment
    original_env = {}
    env_vars = [
        'JWT_SECRET_KEY',
        'RAG_LLM',
        'VECTOR_DB',
        'MILVUS_HOST',
        'PROJECT_NAME',
        'EMBEDDING_MODEL',
        'CHUNKING_STRATEGY',
        'MAX_CHUNK_SIZE',
        'USE_NEW_CONFIG'
    ]
    for var in env_vars:
        if var in os.environ:
            original_env[var] = os.environ[var]
            del os.environ[var]
    
    yield
    
    # Restore original environment
    for var in env_vars:
        if var in original_env:
            os.environ[var] = original_env[var]
        elif var in os.environ:
            del os.environ[var]


@pytest.fixture
def base_environment():
    """Set up base environment variables required for most tests."""
    os.environ['JWT_SECRET_KEY'] = 'test_secret_key'
    os.environ['RAG_LLM'] = 'test_llm'
    yield