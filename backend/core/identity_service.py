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
        Get the mock user ID from environment variables or generate a default.

        This allows for a consistent mock user ID during testing and development,
        which can be overridden via environment variables if needed.

        The environment variable `MOCK_USER_ID` is used to source the ID.

        Returns:
            UUID: The mock user ID.
        """
        mock_id_str = os.getenv("MOCK_USER_ID", "9bae4a21-718b-4c8b-bdd2-22857779a85b")
        try:
            return UUID(mock_id_str)
        except ValueError:
            # Fallback to a hardcoded valid UUID if the env var is invalid
            return UUID("9bae4a21-718b-4c8b-bdd2-22857779a85b")