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
        Get the mock user ID from environment variables or generate a new one.

        This allows for a consistent mock user ID during testing and development,
        which can be overridden via environment variables if needed.

        The environment variable `MOCK_USER_ID` is used to source the ID.
        If not set, generates a new UUID (note: will be different on each call).

        Returns:
            UUID: The mock user ID.

        Raises:
            ValueError: If MOCK_USER_ID is set but invalid.
        """
        mock_id_str = os.getenv("MOCK_USER_ID")
        if mock_id_str:
            try:
                return UUID(mock_id_str)
            except ValueError as e:
                raise ValueError(f"Invalid MOCK_USER_ID in environment: {mock_id_str}") from e

        # Generate a new UUID if not specified
        # Note: This will be different each time unless user is persisted in database
        return IdentityService.generate_id()
