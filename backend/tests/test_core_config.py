"""Tests for core configuration settings."""

import os
import pytest
from unittest.mock import patch, mock_open
from core.config import Settings, LegacySettings, USE_NEW_CONFIG

# Required for tests
TEST_JWT_KEY = "test-jwt-secret-key"

@pytest.fixture
def mock_new_config():
    """Fixture to mock USE_NEW_CONFIG."""
    with patch('core.config.USE_NEW_CONFIG', True):
        yield

@pytest.fixture
def mock_legacy_config():
    """Fixture to mock USE_NEW_CONFIG."""
    with patch('core.config.USE_NEW_CONFIG', False):
        yield

def test_new_settings(mock_new_config):
    """Test new configuration values."""
    settings = Settings(jwt_secret_key=TEST_JWT_KEY)
    
    # Test default values
    assert settings.vector_db == "milvus"
    assert settings.llm_concurrency == 10
    assert settings.milvus_host == "localhost"
    assert settings.milvus_port == 19530
    assert settings.project_name == "rag_modulo"
    assert settings.python_version == "3.11"

def test_legacy_settings(mock_legacy_config):
    """Test legacy configuration values."""
    settings = LegacySettings(jwt_secret_key=TEST_JWT_KEY)
    
    # Test legacy-specific values
    assert settings.chunking_strategy == "fixed"
    assert settings.embedding_model == "sentence-transformers/all-minilm-l6-v2"
    assert settings.number_of_results == 5
    assert settings.min_chunk_size == 100
    assert settings.max_chunk_size == 400
    assert settings.embedding_dim == 384

def test_new_env_override(mock_new_config):
    """Test environment variable overrides for new config."""
    test_env = {
        'JWT_SECRET_KEY': TEST_JWT_KEY,
        'WATSONX_INSTANCE_ID': 'test-instance',
        'WATSONX_APIKEY': 'test-key',
        'WATSONX_URL': 'test-url',
        'VECTOR_DB': 'test-db',
        'MILVUS_HOST': 'test-host',
        'MILVUS_PORT': '9999',
        'PROJECT_NAME': 'test-project'
    }
    
    with patch.dict(os.environ, test_env):
        settings = Settings()
        
        assert settings.wx_project_id == 'test-instance'
        assert settings.wx_api_key == 'test-key'
        assert settings.wx_url == 'test-url'
        assert settings.vector_db == 'test-db'
        assert settings.milvus_host == 'test-host'
        assert settings.milvus_port == 9999
        assert settings.project_name == 'test-project'

def test_legacy_env_override(mock_legacy_config):
    """Test environment variable overrides for legacy config."""
    test_env = {
        'JWT_SECRET_KEY': TEST_JWT_KEY,
        'WATSONX_INSTANCE_ID': 'test-instance',
        'CHUNKING_STRATEGY': 'semantic',
        'MIN_CHUNK_SIZE': '200',
        'EMBEDDING_MODEL': 'test-model',
        'NUMBER_OF_RESULTS': '10'
    }
    
    with patch.dict(os.environ, test_env):
        settings = LegacySettings()
        
        assert settings.wx_project_id == 'test-instance'
        assert settings.chunking_strategy == 'semantic'
        assert settings.min_chunk_size == 200
        assert settings.embedding_model == 'test-model'
        assert settings.number_of_results == 10

def test_new_optional_settings(mock_new_config):
    """Test optional settings behavior in new config."""
    settings = Settings(jwt_secret_key=TEST_JWT_KEY)
    
    # Test optional fields have correct default values
    assert settings.wx_project_id is None
    assert settings.wx_api_key is None
    assert settings.wx_url is None
    assert settings.data_dir is None
    assert settings.ibm_client_id is None
    assert settings.ibm_client_secret is None

def test_legacy_optional_settings(mock_legacy_config):
    """Test optional settings behavior in legacy config."""
    settings = LegacySettings(jwt_secret_key=TEST_JWT_KEY)
    
    # Test optional fields have correct default values
    assert settings.wx_project_id is None
    assert settings.wx_api_key is None
    assert settings.wx_url is None
    assert settings.data_dir is None
    assert settings.collection_name is None

def test_new_database_settings(mock_new_config):
    """Test database configuration in new config."""
    settings = Settings(jwt_secret_key=TEST_JWT_KEY)
    
    # Test database defaults
    assert settings.collectiondb_user == "rag_modulo_user"
    assert settings.collectiondb_host == "localhost"
    assert settings.collectiondb_port == 5432
    assert settings.collectiondb_name == "rag_modulo"

def test_legacy_database_settings(mock_legacy_config):
    """Test database configuration in legacy config."""
    settings = LegacySettings(jwt_secret_key=TEST_JWT_KEY)
    
    # Test database defaults
    assert settings.collectiondb_user == "rag_modulo_user"
    assert settings.collectiondb_host == "localhost"
    assert settings.collectiondb_port == 5432
    assert settings.collectiondb_name == "rag_modulo"

def test_new_frontend_settings(mock_new_config):
    """Test frontend configuration in new config."""
    settings = Settings(jwt_secret_key=TEST_JWT_KEY)
    
    # Test frontend defaults
    assert settings.react_app_api_url == "/api"
    assert settings.frontend_url == "http://localhost:3000"
    assert settings.frontend_callback == "/callback"

def test_legacy_frontend_settings(mock_legacy_config):
    """Test frontend configuration in legacy config."""
    settings = LegacySettings(jwt_secret_key=TEST_JWT_KEY)
    
    # Test frontend defaults
    assert settings.react_app_api_url == "/api"
    assert settings.frontend_url == "http://localhost:3000"
    assert settings.frontend_callback == "/callback"

def test_env_file_loading():
    """Test loading settings from env file."""
    env_content = (
        "WATSONX_INSTANCE_ID=env-instance\n"
        "WATSONX_APIKEY=env-key\n"
        "VECTOR_DB=env-db\n"
        "PROJECT_NAME=env-project\n"
        "JWT_SECRET_KEY=env-jwt-key\n"
    )
    
    with patch('builtins.open', mock_open(read_data=env_content)):
        with patch('os.path.exists', return_value=True):
            with patch('core.config.USE_NEW_CONFIG', True):
                settings = Settings()
                assert settings.wx_project_id == 'env-instance'
                assert settings.wx_api_key == 'env-key'
                assert settings.vector_db == 'env-db'
                assert settings.project_name == 'env-project'

def test_required_settings():
    """Test required settings validation."""
    # Test that jwt_secret_key is required in both configs
    with pytest.raises(ValueError):
        Settings(jwt_secret_key=None)
    
    with pytest.raises(ValueError):
        LegacySettings(jwt_secret_key=None)

def test_jwt_settings():
    """Test JWT configuration."""
    # Test both configs have same JWT defaults
    new_settings = Settings(jwt_secret_key=TEST_JWT_KEY)
    legacy_settings = LegacySettings(jwt_secret_key=TEST_JWT_KEY)
    
    assert new_settings.jwt_secret_key == TEST_JWT_KEY
    assert new_settings.jwt_algorithm == "HS256"
    assert legacy_settings.jwt_secret_key == TEST_JWT_KEY
    assert legacy_settings.jwt_algorithm == "HS256"

def test_oidc_endpoints():
    """Test OIDC endpoint configurations."""
    test_endpoints = {
        'JWT_SECRET_KEY': TEST_JWT_KEY,
        'OIDC_DISCOVERY_ENDPOINT': 'https://test.discovery',
        'OIDC_AUTH_URL': 'https://test.auth',
        'OIDC_TOKEN_URL': 'https://test.token',
        'OIDC_USERINFO_ENDPOINT': 'https://test.userinfo',
        'OIDC_INTROSPECTION_ENDPOINT': 'https://test.introspection'
    }
    
    with patch.dict(os.environ, test_endpoints):
        # Test both configs handle OIDC settings
        with patch('core.config.USE_NEW_CONFIG', True):
            new_settings = Settings()
            assert new_settings.oidc_discovery_endpoint == 'https://test.discovery'
            assert new_settings.oidc_auth_url == 'https://test.auth'
            
        with patch('core.config.USE_NEW_CONFIG', False):
            legacy_settings = LegacySettings()
            assert legacy_settings.oidc_discovery_endpoint == 'https://test.discovery'
            assert legacy_settings.oidc_auth_url == 'https://test.auth'
