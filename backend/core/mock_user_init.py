"""
Mock user initialization module.
Ensures mock users are properly created with full initialization.
"""

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from core.config import Settings
from rag_solution.schemas.user_schema import UserInput
from rag_solution.services.user_service import UserService

logger = logging.getLogger(__name__)

MOCK_USER_CONFIG = {
    "default": {
        "id": UUID("9bae4a21-718b-4c8b-bdd2-22857779a85b"),
        "ibm_id": "mock-user-ibm-id",
        "email": "test@example.com",
        "name": "Test User",
        "role": "admin",
    }
}


def ensure_mock_user_exists(db: Session, settings: Settings, user_key: str = "default") -> UUID:
    """
    Ensure a mock user exists with full initialization.

    This function uses the UserService to properly create the user
    with all required components:
    - User record
    - Prompt templates (RAG_QUERY, QUESTION_GENERATION)
    - LLM provider assignment
    - LLM parameters
    - Pipeline configuration

    Returns:
        UUID: The user's ID
    """
    config = MOCK_USER_CONFIG.get(user_key, MOCK_USER_CONFIG["default"])

    try:
        user_service = UserService(db, settings)

        # Try to get existing user first
        existing_user = user_service.user_repository.get_by_ibm_id(str(config["ibm_id"]))
        if existing_user:
            logger.debug("Mock user already exists: %s", existing_user.id)
            return existing_user.id

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
        # Return the default UUID even if creation failed
        return UUID(str(config["id"]))
