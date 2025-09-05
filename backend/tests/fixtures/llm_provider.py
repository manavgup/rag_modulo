"""Provider fixtures for pytest."""

import pytest
from pydantic import UUID4, SecretStr

from core.logging_utils import get_logger
from rag_solution.generation.providers.base import LLMBase
from rag_solution.generation.providers.factory import LLMProviderFactory
from rag_solution.schemas.llm_provider_schema import LLMProviderInput

logger = get_logger("tests.fixtures.llm_provider")


@pytest.fixture(scope="session")
def base_provider_input() -> LLMProviderInput:
    """Create base provider input for testing."""
    return LLMProviderInput(
        name="test-provider",
        base_url="https://api.test.com",
        api_key=SecretStr("test-key"),
        project_id="test-project",
        org_id="test-org",
        is_active=True,
        is_default=True,
        user_id=UUID4(),
    )


@pytest.fixture
def get_watsonx(provider_factory: LLMProviderFactory) -> LLMBase:
    """Get WatsonX provider instance."""
    return provider_factory.get_provider("watsonx")
