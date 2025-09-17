"""Mock authentication utilities for testing and development.

This module provides centralized mock authentication functionality
with configurable tokens and consistent behavior across the application.
"""

import logging
import os
import uuid
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from core.config import Settings, get_settings
from rag_solution.schemas.user_schema import UserInput
from rag_solution.services.user_service import UserService

logger = logging.getLogger(__name__)


def get_mock_token() -> str:
    """Get the configured mock authentication token.

    Returns the mock token from environment variable or default.
    Uses a memorable format like 'dev-0000-0000-0000' by default.

    Returns:
        str: The mock authentication token
    """
    settings = get_settings()
    return settings.mock_token


def is_mock_token(token: str) -> bool:
    """Check if a token is a recognized mock token.

    Args:
        token: The token to check

    Returns:
        bool: True if the token is a mock token
    """
    if not token:
        return False

    mock_token = get_mock_token()

    # Check for exact match with configured mock token
    if token == mock_token:
        return True

    # Check for legacy hardcoded mock token (for backward compatibility)
    if token == "mock_token_for_testing":
        return True

    # Check for any token starting with "mock_token_"
    if token.startswith("mock_token_"):
        return True

    # Check for dev tokens (new pattern)
    return bool(token.startswith("dev-"))


def create_mock_user_data(user_uuid: str | None = None) -> dict[str, Any]:
    """Create mock user data for testing.

    Args:
        user_uuid: Required user UUID to use

    Returns:
        dict: Mock user data

    Raises:
        ValueError: If user_uuid is not provided
    """
    if not user_uuid:
        raise ValueError("user_uuid is required for mock user data")

    return {
        "id": "test_user_id",
        "email": "test@example.com",
        "name": "Test User",
        "uuid": user_uuid,
        "role": "admin",
    }


def is_bypass_mode_active() -> bool:
    """Check if authentication bypass mode is active.

    Returns:
        bool: True if authentication should be bypassed
    """
    skip_auth = os.getenv("SKIP_AUTH", "false").lower() == "true"
    development_mode = os.getenv("DEVELOPMENT_MODE", "false").lower() == "true"
    testing_mode = os.getenv("TESTING", "false").lower() == "true"
    return skip_auth or development_mode or testing_mode


def ensure_mock_user_exists(db: Session, settings: Settings, user_key: str = "default") -> UUID:  # pylint: disable=unused-argument
    """
    Ensure a mock user exists with full initialization.

    This function uses the UserService to properly create the user
    with all required components:
    - User record
    - Prompt templates (RAG_QUERY, QUESTION_GENERATION)
    - LLM provider assignment
    - LLM parameters
    - Pipeline configuration

    Uses environment variables for configuration instead of hardcoded values.

    Returns:
        UUID: The user's ID
    """
    # Get mock user configuration from environment variables
    config = {
        "ibm_id": os.getenv("MOCK_USER_IBM_ID", "mock-user-ibm-id"),
        "email": os.getenv("MOCK_USER_EMAIL", "test@example.com"),
        "name": os.getenv("MOCK_USER_NAME", "Test User"),
        "role": os.getenv("MOCK_USER_ROLE", "admin"),
    }

    try:
        user_service = UserService(db, settings)

        # Try to get existing user first
        try:
            existing_user = user_service.user_repository.get_by_ibm_id(str(config["ibm_id"]))
            logger.debug("Mock user already exists: %s", existing_user.id)
            return existing_user.id
        except (ValueError, AttributeError, TypeError):
            # User doesn't exist, proceed to create
            pass

        # Create new user with full initialization
        user_input = UserInput(
            ibm_id=str(config["ibm_id"]), email=str(config["email"]), name=str(config["name"]), role=str(config["role"])
        )

        logger.info("Creating mock user: %s", config["email"])
        user = user_service.create_user(user_input)
        logger.info("Mock user created successfully: %s", user.id)

        return user.id

    except (ValueError, KeyError, AttributeError) as e:
        logger.error("Failed to ensure mock user exists: %s", str(e))
        # Generate a random UUID if creation failed
        return uuid.uuid4()
