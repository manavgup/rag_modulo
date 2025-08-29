"""LLM infrastructure fixtures for pytest."""

import pytest

from core.logging_utils import get_logger
from rag_solution.generation.providers.factory import LLMProviderFactory
from rag_solution.schemas.llm_parameters_schema import LLMParametersInput
from rag_solution.schemas.user_schema import UserOutput
from rag_solution.services.llm_parameters_service import LLMParametersService

logger = get_logger("tests.fixtures.llm")


@pytest.fixture
def provider_factory(db_session):
    """Create a provider factory for testing."""
    return LLMProviderFactory(db_session)


@pytest.fixture(scope="session")
def base_llm_parameters(llm_parameters_service: LLMParametersService, base_user: UserOutput):
    """Create default LLM parameters using service."""
    params = LLMParametersInput(
        name="default",
        description="Default test parameters",
        max_new_tokens=1000,
        temperature=0.7,
        top_k=50,
        top_p=1.0,
        repetition_penalty=1.1,
        is_default=True,
    )
    return llm_parameters_service.create_parameters(base_user.id, params)


@pytest.fixture
def get_watsonx(provider_factory: LLMProviderFactory):
    """Get WatsonX provider instance."""
    return provider_factory.get_provider("watsonx")
