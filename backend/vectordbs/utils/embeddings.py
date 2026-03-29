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
    text: str | list[str],
    settings: Settings,
    provider_name: str | None = None,
    provider_factory: "LLMProviderFactory | None" = None,
) -> list[list[float]]:
    """
    Get embeddings using the provider-based approach with rate limiting.

    This is a utility function for vector stores to access embedding functionality
    without requiring complex dependency injection.

    Args:
        text: Single text string or list of text strings to embed
        settings: Settings object containing configuration
        provider_name: Optional provider name. Defaults to settings.llm_provider_name or "watsonx"
        provider_factory: Optional pre-constructed LLMProviderFactory.  When
            provided, skips creating a new DB session and factory (saves ~2 queries).

    Returns:
        List of embedding vectors

    Raises:
        LLMProviderError: If provider-related errors occur
        SQLAlchemyError: If database-related errors occur
        Exception: If other unexpected errors occur
    """
    resolved_name = provider_name or getattr(settings, "llm_provider_name", "watsonx")

    # Fast path: reuse caller-supplied factory (no new DB session needed)
    if provider_factory is not None:
        try:
            provider = provider_factory.get_provider(resolved_name)
            return provider.get_embeddings(text)
        except LLMProviderError:
            raise
        except Exception as e:
            logger.error("Error using supplied provider_factory: %s", e)
            raise

    # Legacy path: create session and factory on the fly
    session_factory = create_session_factory()
    db = None  # Initialize to None to prevent NameError in finally block

    try:
        db = session_factory()
        factory = LLMProviderFactory(db, settings)
        provider = factory.get_provider(resolved_name)
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
