# prompt_template.py
"""Test fixtures for Prompt Templates."""

import pytest

from rag_solution.schemas.prompt_template_schema import PromptTemplateInput, PromptTemplateOutput, PromptTemplateType
from rag_solution.schemas.user_schema import UserOutput
from rag_solution.services.prompt_template_service import PromptTemplateService

# These are now data structures to help create templates, not direct Pydantic inputs
RAG_TEMPLATE_DATA = {
    "name": "Base RAG Template",
    "system_prompt": "You are a helpful RAG AI assistant.",
    "template_type": PromptTemplateType.CUSTOM,
    "template_format": "Context: {context}\nQuery: {query}\nResponse:",
    "input_variables": {"context": "Relevant context for the query", "query": "User's query"},
    "context_strategy": {"type": "simple"},
    "max_context_length": 1000,
}

QUESTION_GEN_TEMPLATE_DATA = {
    "name": "Base Question Gen Template",
    "system_prompt": "You are a helpful question generation AI.",
    "template_type": PromptTemplateType.CUSTOM,
    "template_format": "Context: {context}\nGenerate an insightful question:",
    "input_variables": {"context": "Text to generate a question from"},
    "context_strategy": {"type": "simple"},
    "max_context_length": 1000,
}


@pytest.fixture(scope="session")
def base_rag_prompt_template_input(base_user: UserOutput):
    """Create a base input for RAG prompt template."""
    template_data = RAG_TEMPLATE_DATA.copy()
    template_data["user_id"] = base_user.id
    return template_data


@pytest.fixture(scope="session")
def base_question_gen_template_input(base_user: UserOutput):
    """Create a base input for Question Generation template."""
    template_data = QUESTION_GEN_TEMPLATE_DATA.copy()
    template_data["user_id"] = base_user.id
    return template_data


@pytest.fixture(scope="session")
def base_prompt_template_input(base_user: UserOutput) -> dict:
    """Create a base prompt template input for testing."""
    return {
        "name": "Base Test Template",
        "user_id": base_user.id,
        "template_type": PromptTemplateType.CUSTOM,
        "system_prompt": "You are a helpful AI assistant for testing.",
        "template_format": "Here is the context: {context}\nQuestion: {question}\nAnswer:",
        "input_variables": {"context": "The input context to consider", "question": "The question to answer"},
        "example_inputs": {"context": "Sample context for testing", "question": "Sample test question"},
        "context_strategy": {"type": "simple"},
        "max_context_length": 1000,
        "is_default": True,
    }


@pytest.fixture(scope="session")
def base_prompt_template(
    session_db,
    base_user: UserOutput,
    session_prompt_template_service: PromptTemplateService,
    base_prompt_template_input,
    ensure_watsonx_provider,
) -> PromptTemplateOutput:
    input_with_user = PromptTemplateInput(**base_prompt_template_input).model_copy(
        update={"provider_id": ensure_watsonx_provider.id, "model_id": ensure_watsonx_provider.id}
    )
    return session_prompt_template_service.create_template(input_with_user)


@pytest.fixture(scope="session")
def base_rag_prompt_template(
    session_db, base_user, session_prompt_template_service, base_rag_prompt_template_input, ensure_watsonx_provider
) -> PromptTemplateOutput:
    """Create RAG prompt template in the database."""
    input_with_user = PromptTemplateInput(**base_rag_prompt_template_input).model_copy(
        update={"provider_id": ensure_watsonx_provider.id, "model_id": ensure_watsonx_provider.id}
    )
    return session_prompt_template_service.create_template(input_with_user)


@pytest.fixture(scope="session")
def base_question_gen_template(
    session_db, base_user, session_prompt_template_service, base_question_gen_template_input, ensure_watsonx_provider
) -> PromptTemplateOutput:
    """Create question generation template in the database."""
    input_with_user = PromptTemplateInput(**base_question_gen_template_input).model_copy(
        update={"provider_id": ensure_watsonx_provider.id, "model_id": ensure_watsonx_provider.id}
    )
    return session_prompt_template_service.create_template(input_with_user)


@pytest.fixture(scope="session")
def base_multiple_prompt_templates(
    base_prompt_template, base_rag_prompt_template, base_question_gen_template
) -> dict[str, PromptTemplateOutput]:
    """Create multiple prompt template configurations."""
    return {"base": base_prompt_template, "rag": base_rag_prompt_template, "question_gen": base_question_gen_template}
