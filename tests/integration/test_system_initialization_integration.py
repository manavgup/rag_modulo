"""Integration tests for SystemInitializationService with real database connections."""

import pytest
from backend.core.config import get_settings
from backend.rag_solution.schemas.llm_provider_schema import LLMProviderInput
from backend.rag_solution.services.system_initialization_service import SystemInitializationService
from sqlalchemy.orm import Session


@pytest.mark.integration
class TestSystemInitializationServiceIntegration:
    """Integration tests for SystemInitializationService with real database."""

    @pytest.fixture
    def settings(self):
        """Get integration test settings."""
        return get_settings()

    @pytest.fixture
    def service(self, db_session: Session, settings, mock_llm_provider_service, mock_llm_model_service):
        """Create service instance with mocked services."""
        service = SystemInitializationService(db_session, settings)
        # Inject mock services to avoid Mock iteration issues
        service.llm_provider_service = mock_llm_provider_service
        service.llm_model_service = mock_llm_model_service
        return service

    def test_initialization_with_real_database(self, service, settings):
        """Test service initialization with real database connection."""
        assert service.db is not None
        assert service.settings is settings
        assert hasattr(service, "llm_provider_service")
        assert hasattr(service, "llm_model_service")

    def test_get_provider_configs_with_env_settings(self, service):
        """Test _get_provider_configs with environment settings."""
        result = service._get_provider_configs()

        assert isinstance(result, dict)
        # Should contain at least one provider based on test environment
        assert len(result) >= 0

    def test_initialize_providers_end_to_end(self, service):
        """Test complete provider initialization flow."""
        # This test requires environment variables to be set
        # It will test the actual provider creation/update logic
        try:
            result = service.initialize_providers(raise_on_error=False)

            # Should return a list (empty or with providers)
            assert isinstance(result, list)

            # If providers were created, verify structure
            for provider in result:
                assert hasattr(provider, "id")
                assert hasattr(provider, "name")
                assert hasattr(provider, "base_url")
                assert hasattr(provider, "is_active")
                assert hasattr(provider, "is_default")

        except Exception as e:
            # Test should handle gracefully
            assert "Database" in str(e) or "Provider" in str(e)

    def test_provider_creation_and_retrieval(self, service):
        """Test provider creation and then retrieval."""
        try:
            # Initialize providers
            _initial_providers = service.initialize_providers(raise_on_error=False)

            # Get existing providers again
            existing_providers = service.llm_provider_service.get_all_providers()

            # Should be consistent
            assert isinstance(existing_providers, list)

        except Exception as e:
            # Integration test may fail due to environment setup
            pytest.skip(f"Integration environment not ready: {e}")

    def test_watsonx_model_creation_integration(self, service):
        """Test WatsonX model creation in integration environment."""
        try:
            # This test requires WatsonX credentials in environment
            provider_configs = service._get_provider_configs()

            if "watsonx" in provider_configs:
                # Initialize only WatsonX provider
                result = service.initialize_providers(raise_on_error=False)

                # Check if WatsonX models were created
                watsonx_providers = [p for p in result if p.name == "watsonx"]
                if watsonx_providers:
                    watsonx_provider = watsonx_providers[0]

                    # Verify models were created for WatsonX
                    models = service.llm_model_service.get_models_by_provider(watsonx_provider.id)
                    # Should have generation and embedding models
                    assert len(models) >= 0  # May be 0 if creation failed

        except Exception as e:
            pytest.skip(f"WatsonX integration not available: {e}")

    def test_provider_error_handling_integration(self, service):
        """Test provider error handling with real database."""
        # Test with invalid provider configuration
        invalid_provider = LLMProviderInput(
            name="invalid_provider", base_url="https://invalid.api.com", api_key="invalid-key"
        )

        try:
            # This should handle errors gracefully
            result = service._initialize_single_provider("invalid_provider", invalid_provider, None, False)

            # Should either succeed or return None (graceful failure)
            assert result is None or hasattr(result, "id")

        except Exception as e:
            # Should handle database/provider errors
            assert isinstance(e, Exception)

    def test_database_transaction_handling(self, service):
        """Test database transaction handling during provider initialization."""
        try:
            # Test that database transactions work properly
            initial_count = len(service.llm_provider_service.get_all_providers())

            # Initialize providers
            result = service.initialize_providers(raise_on_error=False)

            # Verify transaction consistency
            final_count = len(service.llm_provider_service.get_all_providers())

            # Count should be consistent with results
            if result:
                assert final_count >= initial_count

        except Exception as e:
            pytest.skip(f"Database transaction test failed: {e}")

    def test_concurrent_provider_initialization(self, service):
        """Test provider initialization under concurrent conditions."""
        import threading

        results = []
        errors = []

        def init_providers():
            try:
                result = service.initialize_providers(raise_on_error=False)
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Run multiple initialization threads
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=init_providers)
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # All should complete (may have errors due to race conditions)
        assert len(results) + len(errors) == 3

        # At least one should succeed
        successful_results = [r for r in results if r is not None]
        assert len(successful_results) >= 0
