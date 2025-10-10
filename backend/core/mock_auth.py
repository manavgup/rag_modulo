"""Mock authentication utilities for testing and development.

This module provides centralized mock authentication functionality
with configurable tokens and consistent behavior across the application.
"""

import logging
import os
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from core.config import Settings, get_settings
from core.identity_service import IdentityService
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


def create_mock_user_data(user_uuid: str | None = None, settings: Settings | None = None) -> dict[str, Any]:
    """Create mock user data for testing.

    Uses settings.mock_user_email and settings.mock_user_name for consistency
    across the application when SKIP_AUTH=true.

    Args:
        user_uuid: Required user UUID to use
        settings: Application settings (defaults to get_settings() if not provided)

    Returns:
        dict: Mock user data

    Raises:
        ValueError: If user_uuid is not provided
    """
    if not user_uuid:
        raise ValueError("user_uuid is required for mock user data")

    # Get settings if not provided
    if settings is None:
        settings = get_settings()

    return {
        "id": "test_user_id",
        "email": settings.mock_user_email,
        "name": settings.mock_user_name,
        "uuid": user_uuid,
        "role": "admin",
    }


def is_bypass_mode_active() -> bool:
    """Check if authentication bypass mode is active.

    When SKIP_AUTH=true, bypass IBM OIDC Provider but still assign mock token and user.

    Returns:
        bool: True if authentication should be bypassed
    """
    return os.getenv("SKIP_AUTH", "false").lower() == "true"


def ensure_mock_user_exists(db: Session, settings: Settings, user_key: str = "default") -> UUID:  # pylint: disable=unused-argument
    """
    Ensure a mock user exists with full initialization.

    This function uses the UserService to properly create the user
    with all required components:
    - User record
    - Prompt templates (RAG_QUERY, QUESTION_GENERATION, PODCAST_GENERATION)
    - LLM provider assignment
    - LLM parameters
    - Pipeline configuration

    Uses settings for configuration to ensure consistency across the application.

    Args:
        db: Database session
        settings: Application settings
        user_key: Key for different mock users (currently unused)

    Returns:
        UUID: The user's ID
    """
    # Get mock user configuration from settings (not os.getenv directly)
    # This ensures consistency with create_mock_user_data() and get_current_user()
    config = {
        "ibm_id": os.getenv("MOCK_USER_IBM_ID", "mock-user-ibm-id"),  # Still use env for IBM ID
        "email": settings.mock_user_email,
        "name": settings.mock_user_name,
        "role": os.getenv("MOCK_USER_ROLE", "admin"),  # Still use env for role
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
            ibm_id=str(config["ibm_id"]),
            email=str(config["email"]),
            name=str(config["name"]),
            role=str(config["role"]),
        )

        logger.info("Creating mock user: %s", config["email"])
        user = user_service.create_user(user_input)
        logger.info("Mock user created successfully: %s", user.id)

        return user.id

    except (ValueError, KeyError, AttributeError) as e:
        logger.error("Failed to ensure mock user exists: %s", str(e))
        # Fallback to the mock user ID from IdentityService if creation fails
        return IdentityService.get_mock_user_id()
