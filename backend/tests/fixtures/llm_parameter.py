"""Test fixtures for LLM Parameters."""

from uuid import uuid4

import pytest

from rag_solution.schemas.llm_parameters_schema import LLMParametersInput, LLMParametersOutput
from rag_solution.schemas.user_schema import UserOutput
from rag_solution.services.llm_parameters_service import LLMParametersService


@pytest.fixture(scope="session")
def default_llm_parameters_input() -> LLMParametersInput:
    """Create a default LLM parameters input for testing."""
    return LLMParametersInput(
        user_id=uuid4(),
        name="Test Default Parameters",
        description="Default parameters for testing",
        max_new_tokens=100,
        temperature=0.7,
        top_k=50,
        top_p=1.0,
        repetition_penalty=1.1,
        is_default=True,
    )


@pytest.fixture
def custom_llm_parameters_input() -> LLMParametersInput:
    """Create a custom LLM parameters input for testing."""
    return LLMParametersInput(
        user_id=uuid4(),
        name="Test Custom Parameters",
        description="Custom parameters for testing",
        max_new_tokens=200,
        temperature=0.9,
        top_k=40,
        top_p=0.9,
        repetition_penalty=1.2,
        is_default=False,
    )


@pytest.fixture
def custom_llm_parameters(base_user: UserOutput, session_llm_parameters_service: LLMParametersService) -> LLMParametersOutput:
    """Create custom LLM parameters in the database."""
    # Create parameters with the correct user_id
    params_input = LLMParametersInput(
        user_id=base_user.id,
        name="Test Custom Parameters",
        description="Custom parameters for testing",
        max_new_tokens=200,
        temperature=0.9,
        top_k=40,
        top_p=0.9,
        repetition_penalty=1.2,
        is_default=False,
    )
    return session_llm_parameters_service.create_parameters(params_input)


@pytest.fixture
def multiple_llm_parameters(base_llm_parameters: LLMParametersOutput, custom_llm_parameters: LLMParametersOutput) -> dict[str, LLMParametersOutput]:
    """Create multiple LLM parameters configurations."""
    return {"default": base_llm_parameters, "custom": custom_llm_parameters}
