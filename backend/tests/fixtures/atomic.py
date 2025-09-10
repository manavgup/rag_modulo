"""Atomic fixtures - Pure data, no dependencies."""

import pytest


@pytest.fixture
def base_llm_parameters_data() -> dict:
    """Pure data for LLM parameters - no external dependencies."""
    return {
        "user_id": 1,
        "name": "Test Default Parameters",
        "description": "Default parameters for testing",
        "max_new_tokens": 100,
        "temperature": 0.7,
        "top_k": 50,
        "top_p": 1.0,
        "repetition_penalty": 1.1,
        "is_default": True,
    }


@pytest.fixture
def base_user_data() -> dict:
    """Pure user data - no external dependencies."""
    return {
        "id": 1,
        "email": "test@example.com",
        "ibm_id": "test_user_123",
        "name": "Test User",
        "role": "user",
    }


@pytest.fixture
def base_collection_data() -> dict:
    """Pure collection data - no external dependencies."""
    return {
        "id": 1,
        "name": "Test Collection",
        "description": "A test collection",
        "user_id": 1,
        "is_private": True,
    }


@pytest.fixture
def base_team_data() -> dict:
    """Pure team data - no external dependencies."""
    return {
        "id": 1,
        "name": "Test Team",
        "description": "A test team",
        "user_id": 1,
    }
