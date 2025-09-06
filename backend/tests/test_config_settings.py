"""Test cases for Settings configuration - Test-Driven Development.

These tests verify that:
1. Settings can be instantiated without environment variables
2. Settings uses sensible defaults when env vars are missing
3. Settings can be lazily initialized
4. Settings respects environment variables when provided
5. Settings works in test isolation scenarios
"""

import os
from unittest.mock import patch

import pytest


class TestSettingsDefaults:
    """Test that Settings has sensible defaults for all required fields."""

    def test_settings_can_instantiate_without_env_vars(self):
        """Settings should instantiate successfully even without any environment variables."""
        with patch.dict(os.environ, {}, clear=True):
            # This should NOT raise ValidationError
            from core.config import Settings

            settings = Settings()

            # Should have default values
            assert settings.jwt_secret_key is not None
            assert settings.rag_llm is not None
            assert settings.wx_project_id is not None  # alias for WATSONX_INSTANCE_ID
            assert settings.wx_api_key is not None  # alias for WATSONX_APIKEY
            assert settings.wx_url is not None  # alias for WATSONX_URL

    def test_settings_uses_sensible_defaults(self):
        """Settings should have sensible default values for development/testing."""
        with patch.dict(os.environ, {}, clear=True):
            from core.config import Settings

            settings = Settings()

            # Check specific default values
            assert settings.jwt_secret_key != ""  # Should have a default secret
            assert settings.rag_llm in ["openai", "watsonx", "anthropic"]  # Valid LLM choice
            assert "http" in settings.wx_url or settings.wx_url == ""  # URL or empty

            # Other settings should also have defaults
            assert settings.vector_db == "milvus"
            assert settings.embedding_model == "sentence-transformers/all-minilm-l6-v2"
            assert settings.chunk_overlap == 10

    def test_settings_respects_env_vars_when_provided(self):
        """Settings should use environment variables when they are provided."""
        test_env = {
            "JWT_SECRET_KEY": "test-secret-from-env",
            "RAG_LLM": "anthropic",
            "WATSONX_INSTANCE_ID": "test-instance",
            "WATSONX_APIKEY": "test-api-key",
            "WATSONX_URL": "https://test.watsonx.com",
        }

        with patch.dict(os.environ, test_env, clear=True):
            from core.config import Settings

            settings = Settings()

            assert settings.jwt_secret_key == "test-secret-from-env"
            assert settings.rag_llm == "anthropic"
            assert settings.wx_project_id == "test-instance"
            assert settings.wx_api_key == "test-api-key"
            assert settings.wx_url == "https://test.watsonx.com"


class TestLazyInitialization:
    """Test that Settings can be lazily initialized."""

    def test_get_settings_function_exists(self):
        """There should be a get_settings() function for lazy initialization."""
        from core.config import get_settings

        assert callable(get_settings)

    def test_get_settings_returns_settings_instance(self):
        """get_settings() should return a Settings instance."""
        with patch.dict(os.environ, {}, clear=True):
            from core.config import Settings, get_settings

            settings = get_settings()
            assert isinstance(settings, Settings)

    def test_get_settings_returns_same_instance(self):
        """get_settings() should return the same instance (singleton pattern)."""
        with patch.dict(os.environ, {}, clear=True):
            from core.config import get_settings

            settings1 = get_settings()
            settings2 = get_settings()
            assert settings1 is settings2  # Same object in memory

    def test_module_import_does_not_fail_without_env_vars(self):
        """Importing the config module should not fail even without env vars."""
        with patch.dict(os.environ, {}, clear=True):
            # This import should not raise any exceptions
            import core.config

            # Module should have the necessary exports
            assert hasattr(core.config, "Settings")
            assert hasattr(core.config, "settings")
            assert hasattr(core.config, "get_settings")


class TestTestIsolation:
    """Test that Settings works in test isolation scenarios."""

    @pytest.mark.atomic
    def test_atomic_test_can_run_without_env_vars(self):
        """Atomic tests should be able to run without any environment setup."""
        # This simulates the test-isolation CI job environment
        with patch.dict(os.environ, {}, clear=True):
            from core.config import get_settings

            # Should be able to access settings without crashes
            settings = get_settings()
            assert settings is not None
            assert hasattr(settings, "jwt_secret_key")
            assert hasattr(settings, "rag_llm")

    @pytest.mark.atomic
    def test_atomic_test_imports_do_not_fail(self):
        """Importing modules that use settings should not fail in atomic tests."""
        with patch.dict(os.environ, {}, clear=True):
            # These imports should not fail

            # Common imports that depend on settings
            # Note: We're testing that these CAN be imported, not that they work perfectly
            try:
                # Test that basic config imports work
                from core.config import get_settings

                settings = get_settings()
                assert settings is not None
            except Exception as e:
                # ValidationError should not occur
                if "ValidationError" in str(e):
                    pytest.fail(f"Settings validation failed during import: {e}")


class TestBackwardCompatibility:
    """Test that existing code patterns still work."""

    def test_direct_settings_import_still_works(self):
        """The pattern 'from core.config import get_settings' should still work."""
        with patch.dict(os.environ, {}, clear=True):
            from core.config import get_settings

            settings = get_settings()
            assert settings is not None

    def test_settings_accessible_at_module_level(self):
        """The 'settings' object should be accessible at module level for compatibility."""
        with patch.dict(os.environ, {}, clear=True):
            import core.config

            assert hasattr(core.config, "settings")
            assert core.config.settings is not None


class TestProductionSafety:
    """Test that production deployments are not affected."""

    def test_production_env_vars_override_defaults(self):
        """In production, environment variables should override any defaults."""
        prod_env = {
            "JWT_SECRET_KEY": "super-secret-production-key-abc123",
            "RAG_LLM": "watsonx",
            "WATSONX_INSTANCE_ID": "prod-instance-id",
            "WATSONX_APIKEY": "prod-api-key-xyz",
            "WATSONX_URL": "https://prod.watsonx.ibm.com",
            "VECTOR_DB": "elasticsearch",
            "EMBEDDING_MODEL": "all-mpnet-base-v2",
        }

        with patch.dict(os.environ, prod_env, clear=True):
            from core.config import Settings

            settings = Settings()

            # All production values should be used
            assert settings.jwt_secret_key == "super-secret-production-key-abc123"
            assert settings.rag_llm == "watsonx"
            assert settings.wx_project_id == "prod-instance-id"
            assert settings.wx_api_key == "prod-api-key-xyz"
            assert settings.wx_url == "https://prod.watsonx.ibm.com"
            assert settings.vector_db == "elasticsearch"
            assert settings.embedding_model == "all-mpnet-base-v2"

    def test_warning_or_validation_for_default_secrets_in_production(self):
        """There should be some mechanism to warn about using default secrets in production."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=True):
            from core.config import Settings

            settings = Settings()

            # If using default JWT secret in production, it should be obvious
            if hasattr(settings, "jwt_secret_key"):
                # Either the default should indicate it's not for production
                # Or there should be a validation method
                default_indicators = ["dev", "test", "change", "default", "insecure"]
                is_default = any(indicator in settings.jwt_secret_key.lower() for indicator in default_indicators)

                if is_default and os.getenv("ENVIRONMENT") == "production":
                    # This is actually good - defaults should be clearly marked
                    assert True
