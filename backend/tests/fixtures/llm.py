"""LLM infrastructure fixtures for pytest."""

import pytest
from sqlalchemy.orm import Session

from core.logging_utils import get_logger
from rag_solution.generation.providers.base import LLMBase
from rag_solution.generation.providers.factory import LLMProviderFactory
from rag_solution.schemas.llm_parameters_schema import LLMParametersInput, LLMParametersOutput
from rag_solution.schemas.user_schema import UserOutput
from rag_solution.services.llm_parameters_service import LLMParametersService

logger = get_logger("tests.fixtures.llm")


@pytest.fixture
def provider_factory(db_session: Session) -> LLMProviderFactory:
    """Create a provider factory for testing."""
    return LLMProviderFactory(db_session)


@pytest.fixture(scope="session")
def base_llm_parameters(llm_parameters_service: LLMParametersService, base_user: UserOutput) -> LLMParametersOutput:
    """Create default LLM parameters using service."""
    params = LLMParametersInput(
        name="default",
        description="Default test parameters",
        user_id=base_user.id,
        max_new_tokens=1000,
        temperature=0.7,
        top_k=50,
        top_p=1.0,
        repetition_penalty=1.1,
        is_default=True,
    )
    return llm_parameters_service.create_parameters(params)


@pytest.fixture
def get_watsonx(llm_provider_factory: LLMProviderFactory) -> LLMBase:
    """Get WatsonX provider instance."""
    return llm_provider_factory.get_provider("watsonx")
