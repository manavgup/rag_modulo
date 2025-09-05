"""Integration tests for LLMProviderService."""

from uuid import uuid4

import pytest
from pydantic import UUID4, SecretStr

from core.custom_exceptions import ProviderValidationError
from rag_solution.schemas.llm_provider_schema import LLMProviderInput, LLMProviderOutput
from rag_solution.services.llm_provider_service import LLMProviderService


# -------------------------------------------
# 🧪 Provider Creation Tests
# -------------------------------------------
@pytest.mark.atomic
def test_create_provider(llm_provider_service: LLMProviderService, base_provider_input: LLMProviderInput) -> None:
    """Test provider creation."""
    provider = llm_provider_service.create_provider(base_provider_input)

    assert isinstance(provider, LLMProviderOutput)
    assert provider.name == base_provider_input.name
    assert provider.base_url == base_provider_input.base_url
    assert provider.project_id == base_provider_input.project_id
    assert provider.is_active
    assert isinstance(provider.id, UUID4)


def test_create_provider_validation_errors(llm_provider_service: LLMProviderService) -> None:
    """Test provider creation with invalid inputs."""
    # Test invalid name
    with pytest.raises(ProviderValidationError) as exc_info:
        invalid_input = LLMProviderInput(
            name="test@invalid",  # Invalid characters
            base_url="https://test.com",
            api_key=SecretStr("test-key"),
            org_id=None,
            project_id=None,
            is_active=True,
            is_default=False,
            user_id=None,
        )
        llm_provider_service.create_provider(invalid_input)
    assert "name" in str(exc_info.value)

    # Test invalid URL
    with pytest.raises(ProviderValidationError) as exc_info:
        invalid_input = LLMProviderInput(
            name="test-provider",
            base_url="not-a-url",  # Invalid URL
            api_key=SecretStr("test-key"),
            org_id=None,
            project_id=None,
            is_active=True,
            is_default=False,
            user_id=None,
        )
        llm_provider_service.create_provider(invalid_input)
    assert "base_url" in str(exc_info.value)


# -------------------------------------------
# 🧪 Provider Retrieval Tests
# -------------------------------------------
def test_get_provider_by_name(llm_provider_service: LLMProviderService, base_provider_input: LLMProviderInput) -> None:
    """Test getting provider by name."""
    created = llm_provider_service.create_provider(base_provider_input)

    provider = llm_provider_service.get_provider_by_name(base_provider_input.name)
    assert provider is not None
    assert provider.id == created.id
    assert provider.name == created.name

    # Test case insensitive search
    provider = llm_provider_service.get_provider_by_name(base_provider_input.name.upper())
    assert provider is not None
    assert provider.id == created.id


def test_get_provider_by_id(llm_provider_service: LLMProviderService, base_provider_input: LLMProviderInput) -> None:
    """Test getting provider by ID."""
    created = llm_provider_service.create_provider(base_provider_input)

    provider = llm_provider_service.get_provider_by_id(created.id)
    assert provider is not None
    assert provider.id == created.id
    assert provider.name == created.name


def test_get_nonexistent_provider(llm_provider_service: LLMProviderService) -> None:
    """Test getting non-existent provider."""
    result = llm_provider_service.get_provider_by_id(uuid4())
    assert result is None

    result_config = llm_provider_service.get_provider_by_name("nonexistent")
    assert result_config is None


# -------------------------------------------
# 🧪 Provider Update Tests
# -------------------------------------------
def test_update_provider(llm_provider_service: LLMProviderService, base_provider_input: LLMProviderInput) -> None:
    """Test updating provider details."""
    created = llm_provider_service.create_provider(base_provider_input)

    updates = {"base_url": "https://new-url.com", "is_active": False}

    updated = llm_provider_service.update_provider(created.id, updates)
    assert updated is not None
    assert updated.base_url == "https://new-url.com"
    assert not updated.is_active


def test_update_nonexistent_provider(llm_provider_service: LLMProviderService) -> None:
    """Test updating non-existent provider."""
    updates = {"base_url": "https://new-url.com"}
    result = llm_provider_service.update_provider(uuid4(), updates)
    assert result is None


# -------------------------------------------
# 🧪 Provider Listing Tests
# -------------------------------------------
def test_get_all_providers(llm_provider_service: LLMProviderService, base_provider_input: LLMProviderInput) -> None:
    """Test getting all providers."""
    provider1 = llm_provider_service.create_provider(base_provider_input)

    provider2_input = base_provider_input.model_copy(update={"name": "another-provider", "is_active": False})
    provider2 = llm_provider_service.create_provider(provider2_input)

    # Get all providers
    all_providers = llm_provider_service.get_all_providers()
    assert len(all_providers) >= 2
    assert any(p.id == provider1.id for p in all_providers)
    assert any(p.id == provider2.id for p in all_providers)

    # Get only active providers
    active_providers = llm_provider_service.get_all_providers(is_active=True)
    assert any(p.id == provider1.id for p in active_providers)
    assert not any(p.id == provider2.id for p in active_providers)


# -------------------------------------------
# 🧪 Provider Deletion Tests
# -------------------------------------------
def test_delete_provider(llm_provider_service: LLMProviderService, base_provider_input: LLMProviderInput) -> None:
    """Test provider deletion."""
    created = llm_provider_service.create_provider(base_provider_input)

    # Delete provider
    result = llm_provider_service.delete_provider(created.id)
    assert result is True

    # Verify deletion
    provider = llm_provider_service.get_provider_by_id(created.id)
    assert provider is None


def test_delete_nonexistent_provider(llm_provider_service: LLMProviderService) -> None:
    """Test deleting non-existent provider."""
    result = llm_provider_service.delete_provider(uuid4())
    assert result is False


if __name__ == "__main__":
    pytest.main([__file__])
