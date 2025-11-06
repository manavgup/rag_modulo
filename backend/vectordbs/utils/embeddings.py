"""Shared embedding utilities for vector stores.

This module provides common embedding functionality used across all vector store implementations,
eliminating code duplication and ensuring consistent behavior.
"""

import logging

from sqlalchemy.exc import SQLAlchemyError

from core.config import Settings
from core.custom_exceptions import LLMProviderError
from rag_solution.file_management.database import create_session_factory
from rag_solution.generation.providers.factory import LLMProviderFactory

logger = logging.getLogger(__name__)


def get_embeddings_for_vector_store(
    text: str | list[str], settings: Settings, provider_name: str | None = None
) -> list[list[float]]:
    """
    Get embeddings using the provider-based approach with rate limiting.

    This is a utility function for vector stores to access embedding functionality
    without requiring complex dependency injection.

    Args:
        text: Single text string or list of text strings to embed
        settings: Settings object containing configuration
        provider_name: Optional provider name. Defaults to settings.llm_provider_name or "watsonx"

    Returns:
        List of embedding vectors

    Raises:
        LLMProviderError: If provider-related errors occur
        SQLAlchemyError: If database-related errors occur
        Exception: If other unexpected errors occur
    """
    # Create session and get embeddings in one clean flow
    session_factory = create_session_factory()
    db = None  # Initialize to None to prevent NameError in finally block

    try:
        db = session_factory()
        factory = LLMProviderFactory(db, settings)
        # Use provided provider name, fall back to settings, default to watsonx
        provider = factory.get_provider(provider_name or getattr(settings, "llm_provider_name", "watsonx"))
        return provider.get_embeddings(text)
    except LLMProviderError as e:
        logger.error("LLM provider error during embedding generation: %s", e)
        raise
    except SQLAlchemyError as e:
        logger.error("Database error during embedding generation: %s", e)
        raise
    except Exception as e:
        logger.error("Unexpected error during embedding generation: %s", e)
        raise
    finally:
        if db is not None:
            db.close()
