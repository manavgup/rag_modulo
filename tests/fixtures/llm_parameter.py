"""Test fixtures for LLM Parameters."""

import pytest
from uuid import UUID
from rag_solution.schemas.llm_parameters_schema import LLMParametersInput, LLMParametersOutput
from rag_solution.services.llm_parameters_service import LLMParametersService

@pytest.fixture(scope="session")
def default_llm_parameters_input() -> LLMParametersInput:
    """Create a default LLM parameters input for testing."""
    return LLMParametersInput(
        name="Test Default Parameters",
        description="Default parameters for testing",
        max_new_tokens=100,
        temperature=0.7,
        top_k=50,
        top_p=1.0,
        repetition_penalty=1.1,
        is_default=True
    )

@pytest.fixture
def custom_llm_parameters_input() -> LLMParametersInput:
    """Create a custom LLM parameters input for testing."""
    return LLMParametersInput(
        name="Test Custom Parameters",
        description="Custom parameters for testing",
        max_new_tokens=200,
        temperature=0.9,
        top_k=40,
        top_p=0.9,
        repetition_penalty=1.2,
        is_default=False
    )

@pytest.fixture(scope="session")
def base_llm_parameters(base_user, session_llm_parameters_service: LLMParametersService, 
                        default_llm_parameters_input) -> LLMParametersOutput:
    return session_llm_parameters_service.create_parameters(base_user.id, default_llm_parameters_input)

@pytest.fixture
def custom_llm_parameters(
    base_user,
    session_llm_parameters_service,
    custom_llm_parameters_input
) -> LLMParametersOutput:
    """Create custom LLM parameters in the database."""
    return session_llm_parameters_service.create_parameters(base_user.id, custom_llm_parameters_input)

@pytest.fixture
def multiple_llm_parameters(
    base_llm_parameters,
    custom_llm_parameters
) -> dict[str, LLMParametersOutput]:
    """Create multiple LLM parameters configurations."""
    return {
        "default": base_llm_parameters,
        "custom": custom_llm_parameters
    }