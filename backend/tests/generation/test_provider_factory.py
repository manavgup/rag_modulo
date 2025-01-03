"""Tests for LLM provider factory."""

import pytest
from sqlalchemy.orm import Session

from core.custom_exceptions import LLMProviderError
from rag_solution.generation.providers.factory import LLMProviderFactory
from rag_solution.generation.providers.watsonx import WatsonXProvider

@pytest.fixture
def provider_factory(db_session: Session):
    """Create provider factory instance."""
    factory = LLMProviderFactory(db_session)
    yield factory
    # Clean up after each test
    factory.close_all()

def test_get_provider(provider_factory: LLMProviderFactory):
    """Test getting a provider instance."""
    # Get WatsonX provider instance
    provider = provider_factory.get_provider("watsonx")
    
    # Verify instance
    assert provider is not None
    assert isinstance(provider, WatsonXProvider)
    assert provider.client is not None

def test_get_unknown_provider(provider_factory: LLMProviderFactory):
    """Test getting an unknown provider type."""
    with pytest.raises(LLMProviderError) as exc_info:
        provider_factory.get_provider("unknown")
    assert exc_info.value.details["error_type"] == "unknown_provider"

def test_provider_instance_caching(provider_factory: LLMProviderFactory):
    """Test provider instance caching."""
    # Get provider instance twice
    provider1 = provider_factory.get_provider("watsonx")
    provider2 = provider_factory.get_provider("watsonx")
    
    # Verify same instance returned
    assert provider1 is provider2

def test_provider_reinitialization(provider_factory: LLMProviderFactory):
    """Test provider reinitialization when client is None."""
    # Get initial instance
    provider1 = provider_factory.get_provider("watsonx")
    
    # Simulate client failure
    provider1.client = None
    
    # Get provider again
    provider2 = provider_factory.get_provider("watsonx")
    
    # Verify new instance created
    assert provider1 is not provider2
    assert provider2.client is not None

def test_provider_cleanup(provider_factory: LLMProviderFactory):
    """Test provider cleanup."""
    # Get provider instance
    provider = provider_factory.get_provider("watsonx")
    assert provider.client is not None
    assert len(provider_factory._instances) == 1
    
    # Close all providers
    provider_factory.close_all()
    
    # Verify cleanup
    assert len(provider_factory._instances) == 0
    assert provider.client is None

def test_provider_case_insensitive(provider_factory: LLMProviderFactory):
    """Test provider type is case insensitive."""
    # Get provider with different cases
    provider1 = provider_factory.get_provider("WATSONX")
    provider2 = provider_factory.get_provider("watsonx")
    provider3 = provider_factory.get_provider("WatsonX")
    
    # Verify same instance returned
    assert provider1 is provider2 is provider3
