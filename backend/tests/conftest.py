"""Test configuration and fixtures."""

import os
import pytest
from backend.core.config import Settings

@pytest.fixture
def test_settings() -> Settings:
    """Create test settings with minimal required configuration."""
    os.environ['JWT_SECRET_KEY'] = 'test-secret-key'
    os.environ['WATSONX_INSTANCE_ID'] = 'test-instance'
    os.environ['WATSONX_APIKEY'] = 'test-api-key'
    os.environ['WATSONX_URL'] = 'https://test.watsonx.ai'
    
    return Settings()

@pytest.fixture
def mock_db_settings() -> Settings:
    """Create test settings with database configuration."""
    return Settings(
        collectiondb_user='test_user',
        collectiondb_pass='test_pass',
        collectiondb_host='localhost',
        collectiondb_port=5432,
        collectiondb_name='test_db',
        jwt_secret_key='test-key'
    )
