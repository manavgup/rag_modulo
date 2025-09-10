"""E2E fixtures - Full stack fixtures for end-to-end tests."""

from unittest.mock import Mock

import pytest


@pytest.fixture(scope="session")
def full_database_setup():
    """Set up full database for E2E tests."""
    # This would set up the complete database schema
    # For now, we'll use a mock
    return Mock()


@pytest.fixture(scope="session")
def full_llm_provider_setup():
    """Set up full LLM provider for E2E tests."""
    # This would set up the complete LLM provider
    # For now, we'll use a mock
    return Mock()


@pytest.fixture(scope="session")
def full_vector_store_setup():
    """Set up full vector store for E2E tests."""
    # This would set up the complete vector store
    # For now, we'll use a mock
    return Mock()


@pytest.fixture
def base_user_e2e():
    """Create a real user for E2E tests."""
    # This would create a real user in the database
    # For now, we'll use a mock
    return {"id": 1, "email": "e2e-test@example.com", "name": "E2E Test User", "role": "user"}


@pytest.fixture
def base_collection_e2e(base_user_e2e):
    """Create a real collection for E2E tests."""
    # This would create a real collection in the database
    # For now, we'll use a mock
    return {"id": 1, "name": "E2E Test Collection", "description": "A collection for E2E testing", "user_id": base_user_e2e["id"]}


@pytest.fixture
def base_team_e2e(base_user_e2e):
    """Create a real team for E2E tests."""
    # This would create a real team in the database
    # For now, we'll use a mock
    return {"id": 1, "name": "E2E Test Team", "description": "A team for E2E testing", "user_id": base_user_e2e["id"]}
