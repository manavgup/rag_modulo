"""Test fixtures for Prompt Templates."""

from typing import Any

import pytest

from rag_solution.schemas.llm_provider_schema import LLMProviderOutput
from rag_solution.schemas.prompt_template_schema import (
    PromptTemplateInput,
    PromptTemplateOutput,
    PromptTemplateType,
)
from rag_solution.schemas.user_schema import UserOutput
from rag_solution.services.prompt_template_service import PromptTemplateService

# These are now data structures to help create templates, not direct Pydantic inputs
RAG_TEMPLATE_DATA: dict[str, Any] = {
    "name": "Base RAG Template",
    "system_prompt": "You are a helpful RAG AI assistant.",
    "template_type": PromptTemplateType.CUSTOM,
    "template_format": "Context: {context}\nQuery: {query}\nResponse:",
    "input_variables": {"context": "Relevant context for the query", "query": "User's query"},
    "context_strategy": {"type": "simple"},
    "max_context_length": 1000,
}

QUESTION_GEN_TEMPLATE_DATA: dict[str, Any] = {
    "name": "Base Question Gen Template",
    "system_prompt": "You are a helpful question generation AI.",
    "template_type": PromptTemplateType.CUSTOM,
    "template_format": "Context: {context}\nGenerate an insightful question:",
    "input_variables": {"context": "Text to generate a question from"},
    "context_strategy": {"type": "simple"},
    "max_context_length": 1000,
}


@pytest.fixture(scope="session")
def base_rag_prompt_template_input(base_user: UserOutput) -> PromptTemplateInput:
    """Create a base input for RAG prompt template."""
    return PromptTemplateInput(
        name="Base RAG Template",
        user_id=base_user.id,
        system_prompt="You are a helpful RAG AI assistant.",
        template_type=PromptTemplateType.CUSTOM,
        template_format="Context: {context}\nQuery: {query}\nResponse:",
        input_variables={"context": "Relevant context for the query", "query": "User's query"},
        context_strategy={"type": "simple"},
        max_context_length=1000,
    )


@pytest.fixture(scope="session")
def base_question_gen_template_input(base_user: UserOutput) -> PromptTemplateInput:
    """Create a base input for Question Generation template."""
    return PromptTemplateInput(
        name="Base Question Gen Template",
        user_id=base_user.id,
        system_prompt="You are a helpful question generation AI.",
        template_type=PromptTemplateType.CUSTOM,
        template_format="Context: {context}\nGenerate an insightful question:",
        input_variables={"context": "Text to generate a question from"},
        context_strategy={"type": "simple"},
        max_context_length=1000,
    )


@pytest.fixture(scope="session")
def base_prompt_template_input(base_user: UserOutput) -> PromptTemplateInput:
    """Create a base prompt template input for testing."""
    return PromptTemplateInput(
        name="Base Test Template",
        user_id=base_user.id,
        template_type=PromptTemplateType.CUSTOM,
        system_prompt="You are a helpful AI assistant for testing.",
        template_format="Here is the context: {context}\nQuestion: {question}\nAnswer:",
        input_variables={"context": "The input context to consider", "question": "The question to answer"},
        example_inputs={"context": "Sample context for testing", "question": "Sample test question"},
        context_strategy={"type": "simple"},
        max_context_length=1000,
        is_default=True,
    )


@pytest.fixture(scope="session")
def base_prompt_template(
    session_db: Any,
    base_user: UserOutput,
    session_prompt_template_service: PromptTemplateService,
    base_prompt_template_input: PromptTemplateInput,
    ensure_watsonx_provider: LLMProviderOutput,
) -> PromptTemplateOutput:
    """Create default prompt template in the database."""
    return session_prompt_template_service.create_template(base_prompt_template_input)


@pytest.fixture(scope="session")
def base_rag_prompt_template(
    session_db: Any,
    base_user: UserOutput,
    session_prompt_template_service: PromptTemplateService,
    base_rag_prompt_template_input: PromptTemplateInput,
    ensure_watsonx_provider: LLMProviderOutput,
) -> PromptTemplateOutput:
    """Create RAG prompt template in the database."""
    return session_prompt_template_service.create_template(base_rag_prompt_template_input)


@pytest.fixture(scope="session")
def base_question_gen_template(
    session_db: Any,
    base_user: UserOutput,
    session_prompt_template_service: PromptTemplateService,
    base_question_gen_template_input: PromptTemplateInput,
    ensure_watsonx_provider: LLMProviderOutput,
) -> PromptTemplateOutput:
    """Create question generation template in the database."""
    return session_prompt_template_service.create_template(base_question_gen_template_input)


@pytest.fixture(scope="session")
def base_multiple_prompt_templates(
    base_prompt_template: PromptTemplateOutput,
    base_rag_prompt_template: PromptTemplateOutput,
    base_question_gen_template: PromptTemplateOutput,
) -> dict[str, PromptTemplateOutput]:
    """Create multiple prompt template configurations."""
    return {
        "base": base_prompt_template,
        "rag": base_rag_prompt_template,
        "question_gen": base_question_gen_template,
    }
