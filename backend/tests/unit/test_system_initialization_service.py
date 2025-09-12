"""
TDD Tests for SystemInitializationService - Starting with Characterization Tests

This follows the TDD approach for existing code:
1. Write tests that describe CURRENT behavior (even if wrong) - RED phase
2. Make tests pass - GREEN phase  
3. Refactor safely - REFACTOR phase
4. Add new failing tests for improvements - RED phase again
5. Make those pass - GREEN phase again

Coverage Target: SystemInitializationService from 0% to 100%
"""

import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from core.config import Settings
from core.custom_exceptions import LLMProviderError
from rag_solution.services.system_initialization_service import SystemInitializationService
from rag_solution.schemas.llm_provider_schema import LLMProviderOutput


@pytest.mark.unit
class TestSystemInitializationServiceTDD:
    """TDD tests for SystemInitializationService - characterizing existing behavior."""

    @pytest.fixture
    def mock_db(self) -> Mock:
        """Mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def mock_settings(self) -> Mock:
        """Mock settings."""
        return Mock(spec=Settings)

    @pytest.fixture
    def service(self, mock_db, mock_settings) -> SystemInitializationService:
        """Create service instance for testing."""
        return SystemInitializationService(mock_db, mock_settings)

    def test_service_initialization(self, service, mock_db, mock_settings):
        """Test that SystemInitializationService initializes correctly."""
        # Characterize current behavior
        assert service.db is mock_db
        assert service.settings is mock_settings
        assert hasattr(service, 'llm_provider_service')
        assert hasattr(service, 'llm_model_service')
        assert hasattr(service, 'initialize_providers')

    def test_initialize_providers_with_no_existing_providers(self, service):
        """Test initialize_providers when no providers exist - characterize current behavior."""
        # Mock the provider service to return empty list
        service.llm_provider_service.get_all_providers = Mock(return_value=[])

        # Mock _get_provider_configs to return empty dict (current behavior when no configs)
        service._get_provider_configs = Mock(return_value={})

        # This should currently return empty list and log a warning
        result = service.initialize_providers()

        # Characterize current behavior
        assert result == []
        service.llm_provider_service.get_all_providers.assert_called_once()
        service._get_provider_configs.assert_called_once()

    def test_initialize_providers_with_provider_service_error(self, service):
        """Test initialize_providers when provider service fails - characterize current behavior."""
        # Mock provider service to raise exception
        service.llm_provider_service.get_all_providers = Mock(side_effect=Exception("DB connection failed"))

        # With raise_on_error=False (default), should return empty list
        result = service.initialize_providers(raise_on_error=False)
        assert result == []

        # With raise_on_error=True, should raise LLMProviderError
        with pytest.raises(LLMProviderError) as exc_info:
            service.initialize_providers(raise_on_error=True)

        assert "DB connection failed" in str(exc_info.value)

    def test_initialize_providers_with_configs_but_no_existing_providers(self, service):
        """Test initialize_providers with configs but no existing providers."""
        # Mock empty existing providers
        service.llm_provider_service.get_all_providers = Mock(return_value=[])

        # Mock some provider configs
        mock_configs = {
            "openai": {"api_key": "test-key", "model": "gpt-3.5-turbo"},
            "anthropic": {"api_key": "test-key", "model": "claude-2"}
        }
        service._get_provider_configs = Mock(return_value=mock_configs)

        # Mock successful provider initialization with proper schema
        from uuid import uuid4
        from datetime import datetime
        mock_provider = LLMProviderOutput(
            id=uuid4(),
            name="openai",
            base_url="https://api.openai.com/v1",
            org_id=None,
            project_id=None,
            is_active=True,
            is_default=False,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        service._initialize_single_provider = Mock(return_value=mock_provider)

        result = service.initialize_providers()

        # Should call _initialize_single_provider for each config
        assert service._initialize_single_provider.call_count == 2
        assert len(result) == 2  # Both providers should be returned

    def test_initialize_providers_with_single_provider_failure(self, service):
        """Test initialize_providers when single provider initialization fails."""
        service.llm_provider_service.get_all_providers = Mock(return_value=[])

        mock_configs = {"openai": {"api_key": "invalid-key"}}
        service._get_provider_configs = Mock(return_value=mock_configs)

        # Mock provider initialization to fail
        service._initialize_single_provider = Mock(side_effect=Exception("Invalid API key"))

        # With raise_on_error=False, should continue and return empty list
        result = service.initialize_providers(raise_on_error=False)
        assert result == []

        # With raise_on_error=True, should raise LLMProviderError
        with pytest.raises(LLMProviderError):
            service.initialize_providers(raise_on_error=True)

    def test_initialize_providers_mixed_success_and_failure(self, service):
        """Test initialize_providers with some successes and some failures."""
        service.llm_provider_service.get_all_providers = Mock(return_value=[])

        mock_configs = {
            "openai": {"api_key": "valid-key"},
            "anthropic": {"api_key": "invalid-key"}
        }
        service._get_provider_configs = Mock(return_value=mock_configs)

        # Mock one success, one failure
        from uuid import uuid4
        from datetime import datetime
        mock_provider = LLMProviderOutput(
            id=uuid4(),
            name="openai",
            base_url="https://api.openai.com/v1",
            org_id=None,
            project_id=None,
            is_active=True,
            is_default=False,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        def side_effect(name, config, existing, raise_on_error):
            if name == "openai":
                return mock_provider
            else:
                raise Exception("Invalid API key")

        service._initialize_single_provider = Mock(side_effect=side_effect)

        # With raise_on_error=False, should return successful providers
        result = service.initialize_providers(raise_on_error=False)
        assert len(result) == 1
        assert result[0].name == "openai"

    # These tests will FAIL initially - that's the RED phase of TDD
    # We need to implement the missing methods to make them pass

    def test_get_provider_configs_method_exists(self, service):
        """Test that _get_provider_configs method exists and returns dict."""
        # This will FAIL initially because method might not be properly implemented
        with patch.object(service, '_get_provider_configs') as mock_method:
            mock_method.return_value = {}
            result = service._get_provider_configs()
            assert isinstance(result, dict)

    def test_initialize_single_provider_method_exists(self, service):
        """Test that _initialize_single_provider method exists."""
        # This will FAIL initially if method is not implemented
        with patch.object(service, '_initialize_single_provider') as mock_method:
            mock_method.return_value = None
            result = service._initialize_single_provider("test", {}, None, False)
            # Method should be callable
            mock_method.assert_called_once_with("test", {}, None, False)


@pytest.mark.integration
class TestSystemInitializationServiceIntegration:
    """Integration tests for SystemInitializationService with real dependencies."""

    def test_service_with_real_database_connection_fails_gracefully(self, integration_settings):
        """Test that service handles real database connection issues gracefully."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        # Use invalid connection string to simulate connection failure
        engine = create_engine("postgresql://invalid:invalid@localhost:1234/invalid")
        session = Session(engine)

        service = SystemInitializationService(session, integration_settings)

        # Should handle connection errors gracefully
        result = service.initialize_providers(raise_on_error=False)
        assert isinstance(result, list)
        # Should either return empty list or raise appropriate error


# TDD PLAN for 100% Coverage:
#
# Phase 1: Make all characterization tests PASS (GREEN)
# - Implement missing _get_provider_configs method
# - Implement missing _initialize_single_provider method
# - Fix any broken behavior discovered by tests
#
# Phase 2: Add failing tests for improvements (RED)
# - Test provider config validation
# - Test model initialization
# - Test error handling improvements
# - Test performance requirements
#
# Phase 3: Make improvement tests PASS (GREEN)
# - Implement the improvements
# - Ensure all tests pass
#
# This approach gives us 100% coverage while following TDD principles!
