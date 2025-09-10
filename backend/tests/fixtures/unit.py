"""Unit fixtures - Mocked dependencies for unit tests."""

from collections.abc import Generator
from unittest.mock import Mock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_watsonx_imports():
    """Mock WatsonX imports for unit tests to prevent environment variable issues."""
    with (
        patch("vectordbs.utils.watsonx.get_wx_client") as mock_client,
        patch("vectordbs.utils.watsonx.get_model") as mock_model,
        patch("vectordbs.utils.watsonx.generate_text") as mock_generate,
        patch("rag_solution.evaluation.llm_as_judge_evals.init_llm") as mock_init_llm,
    ):
        # Configure mocks
        mock_client.return_value = Mock()
        mock_model.return_value = Mock()
        mock_generate.return_value = "mocked response"
        mock_init_llm.return_value = Mock()

        yield


@pytest.fixture(autouse=True)
def mock_jwt_verification() -> Generator[None, None, None]:
    """Mock JWT verification for unit tests."""
    import jwt

    test_jwt = "mock_token_for_testing"
    test_user = {"sub": "test_user", "email": "test@example.com"}

    def mock_verify(token: str) -> dict[str, str]:
        if token == "mock_token_for_testing" or token == test_jwt:
            return test_user
        raise jwt.InvalidTokenError("Invalid token")

    with (
        patch("auth.oidc.verify_jwt_token", side_effect=mock_verify),
        patch("core.authentication_middleware.verify_jwt_token", side_effect=mock_verify),
    ):
        yield


@pytest.fixture
def mock_user_service():
    """Mock user service for unit tests."""
    service = Mock()
    service.create_user.return_value = {"id": 1, "email": "test@example.com"}
    service.get_user.return_value = {"id": 1, "email": "test@example.com"}
    service.update_user.return_value = {"id": 1, "email": "updated@example.com"}
    service.delete_user.return_value = True
    return service


@pytest.fixture
def mock_collection_service():
    """Mock collection service for unit tests."""
    service = Mock()
    service.create_collection.return_value = {"id": 1, "name": "Test Collection"}
    service.get_collection.return_value = {"id": 1, "name": "Test Collection"}
    service.update_collection.return_value = {"id": 1, "name": "Updated Collection"}
    service.delete_collection.return_value = True
    return service


@pytest.fixture
def mock_team_service():
    """Mock team service for unit tests."""
    service = Mock()
    service.create_team.return_value = {"id": 1, "name": "Test Team"}
    service.get_team.return_value = {"id": 1, "name": "Test Team"}
    service.update_team.return_value = {"id": 1, "name": "Updated Team"}
    service.delete_team.return_value = True
    return service
