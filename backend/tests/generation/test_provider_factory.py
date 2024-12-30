"""Tests for LLM provider factory."""

import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from core.custom_exceptions import LLMProviderError
from rag_solution.generation.providers.factory import LLMProviderFactory
from rag_solution.generation.providers.base import LLMProvider
from rag_solution.services.provider_config_service import ProviderConfigService
from rag_solution.schemas.provider_config_schema import ProviderModelConfigBase

@pytest.fixture
def mock_provider():
    """Mock provider class."""
    class MockProvider(LLMProvider):
        def __init__(self, provider_config_service: ProviderConfigService) -> None:
            super().__init__()
            self.provider_config_service = provider_config_service
            self.client = Mock()
            
        def close(self) -> None:
            self.client = None
    return MockProvider

@pytest.fixture
def mock_config():
    """Mock provider configuration."""
    return ProviderModelConfigBase(
        provider_name="mock",
        model_id="mock-model",
        default_model_id="mock-model",
        api_key="mock-key",
        parameters_id=1
    )

@pytest.fixture
def provider_factory(db_session: Session):
    """Factory fixture with mocked provider."""
    factory = LLMProviderFactory(db_session)
    return factory

def test_get_provider(provider_factory: LLMProviderFactory, mock_provider, mock_config):
    """Test getting a provider instance."""
    # Add mock provider to registry
    provider_factory._providers["mock"] = mock_provider
    
    # Mock config service
    with patch.object(
        provider_factory._provider_config_service,
        'get_provider_config',
        return_value=mock_config
    ):
        # Get provider instance
        provider = provider_factory.get_provider("mock")
        
        # Verify instance
        assert provider is not None
        assert isinstance(provider, mock_provider)
        assert provider.client is not None

def test_get_unknown_provider(provider_factory: LLMProviderFactory):
    """Test getting an unknown provider type."""
    with pytest.raises(LLMProviderError) as exc_info:
        provider_factory.get_provider("unknown")
    assert exc_info.value.details["error_type"] == "unknown_provider"

def test_provider_initialization_error(
    provider_factory: LLMProviderFactory,
    mock_provider
):
    """Test provider initialization error."""
    # Mock provider that fails initialization
    class FailingProvider(mock_provider):
        def __init__(self, provider_config_service: ProviderConfigService) -> None:
            super().__init__(provider_config_service)
            self.client = None  # Simulate initialization failure
    
    # Add failing provider to registry
    provider_factory._providers["failing"] = FailingProvider
    
    # Attempt to get provider
    with pytest.raises(LLMProviderError) as exc_info:
        provider_factory.get_provider("failing")
    assert exc_info.value.details["error_type"] == "initialization_error"

def test_provider_instance_caching(
    provider_factory: LLMProviderFactory,
    mock_provider,
    mock_config
):
    """Test provider instance caching."""
    # Add mock provider to registry
    provider_factory._providers["mock"] = mock_provider
    
    # Mock config service
    with patch.object(
        provider_factory._provider_config_service,
        'get_provider_config',
        return_value=mock_config
    ):
        # Get provider instance twice
        provider1 = provider_factory.get_provider("mock")
        provider2 = provider_factory.get_provider("mock")
        
        # Verify same instance returned
        assert provider1 is provider2

def test_provider_reinitialization(
    provider_factory: LLMProviderFactory,
    mock_provider,
    mock_config
):
    """Test provider reinitialization when client is None."""
    # Add mock provider to registry
    provider_factory._providers["mock"] = mock_provider
    
    # Mock config service
    with patch.object(
        provider_factory._provider_config_service,
        'get_provider_config',
        return_value=mock_config
    ):
        # Get initial instance
        provider1 = provider_factory.get_provider("mock")
        
        # Simulate client failure
        provider1.client = None
        
        # Get provider again
        provider2 = provider_factory.get_provider("mock")
        
        # Verify new instance created
        assert provider1 is not provider2
        assert provider2.client is not None

def test_provider_cleanup(
    provider_factory: LLMProviderFactory,
    mock_provider,
    mock_config
):
    """Test provider cleanup."""
    # Add mock provider to registry
    provider_factory._providers["mock"] = mock_provider
    
    # Mock config service
    with patch.object(
        provider_factory._provider_config_service,
        'get_provider_config',
        return_value=mock_config
    ):
        # Get provider instance
        provider = provider_factory.get_provider("mock")
        assert provider.client is not None
        
        # Close all providers
        provider_factory.close_all()
        
        # Verify cleanup
        assert len(provider_factory._instances) == 0
        assert provider.client is None

def test_provider_case_insensitive(
    provider_factory: LLMProviderFactory,
    mock_provider,
    mock_config
):
    """Test provider type is case insensitive."""
    # Add mock provider to registry
    provider_factory._providers["mock"] = mock_provider
    
    # Mock config service
    with patch.object(
        provider_factory._provider_config_service,
        'get_provider_config',
        return_value=mock_config
    ):
        # Get provider with different cases
        provider1 = provider_factory.get_provider("MOCK")
        provider2 = provider_factory.get_provider("mock")
        provider3 = provider_factory.get_provider("Mock")
        
        # Verify same instance returned
        assert provider1 is provider2 is provider3
