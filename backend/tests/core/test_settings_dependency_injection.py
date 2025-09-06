"""
Test-driven development tests for settings dependency injection architecture.

This module tests the transition from global settings imports to FastAPI
dependency injection pattern using get_settings() function.

Expected behavior:
1. get_settings() returns consistent singleton instance via @lru_cache
2. FastAPI dependency injection works with Depends(get_settings)
3. No settings access during module import (import-time isolation)
4. Proper validation and error handling
5. Mock-friendly behavior in test environments
"""

import os
from unittest.mock import Mock, patch
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

# Test scenarios for settings dependency injection


def test_get_settings_function_exists():
    """Test that get_settings function exists and is callable."""
    from core.config import get_settings

    assert callable(get_settings)
    settings = get_settings()
    assert settings is not None


def test_get_settings_returns_consistent_instance():
    """Test that get_settings returns the same instance (singleton via @lru_cache)."""
    from core.config import get_settings

    settings1 = get_settings()
    settings2 = get_settings()

    # Should return the same instance due to @lru_cache
    assert settings1 is settings2


def test_get_settings_with_environment_variables():
    """Test that get_settings respects environment variables."""
    with patch.dict(os.environ, {"WATSONX_URL": "https://test.example.com", "JWT_SECRET_KEY": "test-secret-key", "RAG_LLM": "openai"}):
        from core.config import get_settings

        # Clear cache to get fresh instance with new env vars
        get_settings.cache_clear()
        settings = get_settings()

        assert settings.wx_url == "https://test.example.com"
        assert settings.jwt_secret_key == "test-secret-key"
        assert settings.rag_llm == "openai"


def test_fastapi_dependency_injection_pattern():
    """Test FastAPI dependency injection with Depends(get_settings)."""
    from core.config import get_settings, Settings

    app = FastAPI()

    @app.get("/test-settings")
    async def test_endpoint(settings: Settings = Depends(get_settings)):
        return {"rag_llm": settings.rag_llm}

    client = TestClient(app)

    with patch.dict(os.environ, {"RAG_LLM": "test-llm"}):
        get_settings.cache_clear()
        response = client.get("/test-settings")

        assert response.status_code == 200
        assert response.json()["rag_llm"] == "test-llm"


def test_no_import_time_settings_access():
    """Test that modules can be imported without accessing settings."""
    # This test verifies that importing modules doesn't trigger settings validation
    # by temporarily making environment invalid

    original_env = os.environ.copy()

    try:
        # Clear all relevant environment variables to make settings invalid
        for key in list(os.environ.keys()):
            if any(prefix in key for prefix in ["WATSONX", "JWT", "RAG", "VECTOR", "MILVUS"]):
                del os.environ[key]

        # This import should NOT fail even with invalid environment
        # because we're not calling get_settings() during import
        from core.config import get_settings

        # The function should exist but not be called during import
        assert callable(get_settings)

        # Only when we call get_settings() should validation occur
        from pydantic import ValidationError

        with pytest.raises(ValidationError):  # Should fail due to missing required fields
            get_settings()

    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)


def test_settings_validation_error_handling():
    """Test proper error handling when settings validation fails."""
    from core.config import get_settings

    # Clear cache to get fresh validation
    get_settings.cache_clear()

    from pydantic import ValidationError

    with patch.dict(os.environ, {}, clear=True), pytest.raises(ValidationError):  # Should be ValidationError from pydantic
        get_settings()


def test_mocked_settings_in_tests():
    """Test that settings can be properly mocked for testing."""
    from core.config import get_settings

    mock_settings = Mock()
    mock_settings.rag_llm = "mocked-llm"
    mock_settings.wx_url = "https://mocked.example.com"

    with patch("core.config.get_settings", return_value=mock_settings):
        settings = get_settings()

        assert settings.rag_llm == "mocked-llm"
        assert settings.wx_url == "https://mocked.example.com"


def test_settings_cache_behavior():
    """Test @lru_cache behavior with cache clearing."""
    from core.config import get_settings

    # Clear cache
    get_settings.cache_clear()

    with patch.dict(os.environ, {"RAG_LLM": "first-value"}):
        settings1 = get_settings()
        first_rag_llm = settings1.rag_llm

    # Change environment but don't clear cache
    with patch.dict(os.environ, {"RAG_LLM": "second-value"}):
        settings2 = get_settings()  # Should return cached instance

        # Should still have first value due to caching
        assert settings2 is settings1
        assert settings2.rag_llm == first_rag_llm

    # Clear cache and try again
    get_settings.cache_clear()
    with patch.dict(os.environ, {"RAG_LLM": "second-value"}):
        settings3 = get_settings()  # Should create new instance

        assert settings3 is not settings1
        assert settings3.rag_llm == "second-value"


def test_legacy_global_settings_deprecated():
    """Test that direct global settings import still works but is deprecated."""
    # This test ensures backward compatibility during transition
    try:
        from core.config import settings

        # Should still work for backward compatibility
        assert settings is not None

        # But should be equivalent to get_settings()
        from core.config import get_settings

        # They should be the same instance
        assert settings is get_settings()

    except ImportError:
        # It's acceptable if global settings has been removed
        pytest.skip("Global settings has been removed - this is expected")


def test_watsonx_utils_no_import_time_execution():
    """Test that watsonx utils don't execute settings access at import time."""
    # Clear environment to make settings invalid
    original_env = os.environ.copy()

    try:
        for key in list(os.environ.keys()):
            if "WATSONX" in key:
                del os.environ[key]

        # This import should NOT fail even with invalid WatsonX config
        # because settings should not be accessed during import
        from vectordbs.utils import watsonx

        # The module should be importable
        assert watsonx is not None

    except ImportError as e:
        # If import fails, it should NOT be due to settings validation
        assert "validation" not in str(e).lower()
        assert "watsonx" not in str(e).lower() or "settings" not in str(e).lower()

    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)


def test_service_layer_dependency_injection():
    """Test that service layer uses dependency injection properly."""
    from core.config import get_settings, Settings

    # Example of how services should use settings
    class MockService:
        def __init__(self, settings: Settings = Depends(get_settings)):
            self.settings = settings

        def get_llm_provider(self):
            return self.settings.rag_llm

    # In FastAPI, this would be injected automatically
    # For testing, we manually inject
    with patch.dict(os.environ, {"RAG_LLM": "test-provider"}):
        get_settings.cache_clear()
        settings = get_settings()
        service = MockService(settings)

        assert service.get_llm_provider() == "test-provider"


def test_database_models_no_import_time_settings():
    """Test that database models don't access settings during import."""
    original_env = os.environ.copy()

    try:
        # Clear database-related environment variables
        for key in list(os.environ.keys()):
            if any(prefix in key for prefix in ["COLLECTIONDB", "POSTGRES", "DB"]):
                del os.environ[key]

        # These imports should NOT fail even with invalid database config
        from rag_solution.models import collection, user, file

        # Modules should be importable
        assert collection is not None
        assert user is not None
        assert file is not None

    except ImportError as e:
        # If import fails, it should NOT be due to settings/database validation
        error_msg = str(e).lower()
        assert not any(term in error_msg for term in ["validation", "database", "connection"])

    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)


def test_logging_utils_resilient_to_mocked_settings():
    """Test that logging utils handle mocked settings gracefully."""

    # Mock settings with Mock object for log_level
    mock_settings = Mock()
    mock_settings.log_level = Mock()  # This should be handled gracefully

    with patch("core.config.get_settings", return_value=mock_settings):
        # This should not raise an error
        from core.logging_utils import get_logger

        logger = get_logger(__name__)
        assert logger is not None

        # Log level should fallback to INFO when mocked
        import logging

        assert logger.level == logging.INFO


# Integration test scenarios


def test_full_fastapi_app_with_settings_injection():
    """Integration test: Full FastAPI app with settings dependency injection."""
    from core.config import get_settings, Settings

    app = FastAPI()

    @app.get("/health")
    async def health_check(settings: Settings = Depends(get_settings)):
        return {"status": "ok", "llm_provider": settings.rag_llm, "vector_db": settings.vector_db}

    @app.get("/config")
    async def get_config(settings: Settings = Depends(get_settings)):
        return {"wx_url": settings.wx_url, "embedding_model": settings.embedding_model}

    client = TestClient(app)

    with patch.dict(os.environ, {"RAG_LLM": "openai", "VECTOR_DB": "milvus", "WATSONX_URL": "https://test.watsonx.com", "EMBEDDING_MODEL": "text-embedding-ada-002"}):
        get_settings.cache_clear()

        # Test health endpoint
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["llm_provider"] == "openai"
        assert data["vector_db"] == "milvus"

        # Test config endpoint
        response = client.get("/config")
        assert response.status_code == 200
        data = response.json()
        assert data["wx_url"] == "https://test.watsonx.com"
        assert data["embedding_model"] == "text-embedding-ada-002"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
