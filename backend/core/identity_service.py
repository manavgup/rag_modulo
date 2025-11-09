"""
Identity Service for centralized UUID generation.

This module provides a centralized service for generating various types of
unique identifiers used throughout the application. This approach ensures
consistency, maintainability, and allows for easier testing by having a
single point of control for ID generation.
"""

import os
import uuid
from uuid import UUID


class IdentityService:
    """A centralized service for generating unique identifiers."""

    # Default mock user ID for testing and development
    DEFAULT_MOCK_USER_ID = UUID("9bae4a21-718b-4c8b-bdd2-22857779a85b")

    # Mock LLM provider and model IDs for stub implementations
    MOCK_LLM_PROVIDER_ID = UUID("11111111-1111-1111-1111-111111111111")
    MOCK_LLM_MODEL_ID = UUID("22222222-2222-2222-2222-222222222222")

    @staticmethod
    def generate_id() -> UUID:
        """
        Generate a new, standard UUID (version 4).

        Returns:
            UUID: A new unique identifier.
        """
        return uuid.uuid4()

    @staticmethod
    def generate_collection_name() -> str:
        """
        Generate a unique and valid collection name for vector databases.

        Vector database collection names often have restrictions on characters
        (e.g., only alphanumeric and underscores). This method ensures the
        generated name is compliant.

        Returns:
            str: A valid collection name.
        """
        return f"collection_{uuid.uuid4().hex}"

    @staticmethod
    def generate_document_id() -> str:
        """
        Generate a unique identifier for a document.

        Returns:
            str: A string representation of a new UUID.
        """
        return str(uuid.uuid4())

    @staticmethod
    def get_mock_user_id() -> UUID:
        """
        Get the mock user ID from environment variables or use the default.

        This allows for a consistent mock user ID during testing and development,
        which can be overridden via environment variables if needed.

        The environment variable `MOCK_USER_ID` is used to source the ID.
        If not set or invalid, returns the default mock user ID.

        Returns:
            UUID: The mock user ID.
        """
        mock_id_str = os.getenv("MOCK_USER_ID")
        if mock_id_str:
            try:
                return UUID(mock_id_str)
            except ValueError:
                # Fall back to default on invalid UUID
                return IdentityService.DEFAULT_MOCK_USER_ID

        # Return default mock user ID
        return IdentityService.DEFAULT_MOCK_USER_ID

    @staticmethod
    def extract_user_id_from_jwt(current_user: dict, field_name: str = "uuid") -> UUID:
        """
        Extract and validate user_id from JWT token payload.

        JWT tokens store user_id as strings, but application code expects UUID objects.
        This method handles the conversion and validation in a centralized location.

        Args:
            current_user: JWT token payload from get_current_user() dependency
            field_name: Field name in JWT payload containing user ID (default: "uuid")

        Returns:
            UUID: Validated user ID as UUID object

        Raises:
            ValueError: If user_id is missing or has invalid format

        Example:
            >>> current_user = {"uuid": "d1f93297-3e3c-42b0-8da7-09efde032c25", ...}
            >>> user_id = IdentityService.extract_user_id_from_jwt(current_user)
            >>> isinstance(user_id, UUID)
            True
        """
        user_id_str = current_user.get(field_name)

        if not user_id_str:
            raise ValueError(f"User ID not found in JWT token (field: {field_name})")

        # Convert string to UUID if needed
        if isinstance(user_id_str, str):
            try:
                return UUID(user_id_str)
            except (ValueError, AttributeError) as e:
                raise ValueError(f"Invalid user ID format in JWT token: {user_id_str}") from e

        # Already a UUID object
        if isinstance(user_id_str, UUID):
            return user_id_str

        raise ValueError(f"Unexpected user ID type in JWT token: {type(user_id_str)}")
