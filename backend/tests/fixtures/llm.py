"""LLM infrastructure fixtures for pytest."""

import pytest
from sqlalchemy.orm import Session

from core.logging_utils import get_logger
from rag_solution.generation.providers.base import LLMBase
from rag_solution.generation.providers.factory import LLMProviderFactory

logger = get_logger("tests.fixtures.llm")


@pytest.fixture(scope="session")
def provider_factory(session_db: Session) -> LLMProviderFactory:
    """Create a provider factory for testing."""
    return LLMProviderFactory(session_db)


@pytest.fixture(scope="session")
def get_watsonx(provider_factory: LLMProviderFactory) -> LLMBase:
    """Get WatsonX provider instance."""
    return provider_factory.get_provider("watsonx")
