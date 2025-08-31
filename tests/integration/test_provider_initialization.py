"""Tests for LLM provider initialization."""

import pytest
from typing import Dict

from rag_solution.generation.providers.watsonx import WatsonXLLM
from rag_solution.generation.providers.openai import OpenAILLM
from rag_solution.generation.providers.anthropic import AnthropicLLM
from rag_solution.services.llm_provider_service import LLMProviderService
from rag_solution.services.llm_parameters_service import LLMParametersService
from rag_solution.services.prompt_template_service import PromptTemplateService
from rag_solution.schemas.llm_parameters_schema import LLMParametersInput, LLMParametersOutput
from rag_solution.schemas.prompt_template_schema import PromptTemplateInput, PromptTemplateType, PromptTemplateOutput


@pytest.fixture
def test_parameters() -> Dict[str, LLMParametersInput]:
    """Test LLM parameters for each provider."""
    return {
        "watsonx": LLMParametersInput(
            name="watsonx-params", temperature=0.7, max_new_tokens=1000, is_default=True
        ),
        "openai": LLMParametersInput(
            name="openai-params", temperature=0.7, max_new_tokens=1000, is_default=True
        ),
        "anthropic": LLMParametersInput(
            name="anthropic-params", temperature=0.7, max_new_tokens=1000, is_default=True
        ),
    }


@pytest.fixture
def test_templates(base_user) -> Dict[str, PromptTemplateInput]:
    """Test prompt templates for each provider."""
    return {
        "watsonx": PromptTemplateInput(
            name="watsonx-template",
            user_id=base_user.id,
            template_type=PromptTemplateType.RAG_QUERY,
            system_prompt="You are a helpful AI assistant.",
            template_format="Context:\n{context}\n\nQuestion:\n{question}\n\nAnswer:\n",
            input_variables={"context": "Retrieved context", "question": "User's question"},
            example_inputs={"context": "Python was created by Guido van Rossum.", "question": "Who created Python?"},
            is_default=True,
        ),
        "openai": PromptTemplateInput(
            name="openai-template",
            user_id=base_user.id,
            template_type=PromptTemplateType.RAG_QUERY,
            system_prompt="You are a helpful AI assistant.",
            template_format="Context:\n{context}\n\nQuestion:\n{question}\n\nAnswer:\n",
            input_variables={"context": "Retrieved context", "question": "User's question"},
            example_inputs={"context": "Python was created by Guido van Rossum.", "question": "Who created Python?"},
            is_default=True,
        ),
        "anthropic": PromptTemplateInput(
            name="anthropic-template",
            user_id=base_user.id,
            template_type=PromptTemplateType.RAG_QUERY,
            system_prompt="You are a helpful AI assistant.",
            template_format="Context:\n{context}\n\nQuestion:\n{question}\n\nAnswer:\n",
            input_variables={"context": "Retrieved context", "question": "User's question"},
            example_inputs={"context": "Python was created by Guido van Rossum.", "question": "Who created Python?"},
            is_default=True,
        ),
    }


@pytest.mark.parametrize(
    "provider_class, provider_key",
    [
        (WatsonXLLM, "watsonx"),
        (OpenAILLM, "openai"),
        (AnthropicLLM, "anthropic"),
    ],
)
def test_provider_initialization(
    db_session, base_user, test_parameters, test_templates, provider_class, provider_key
):
    """Test provider initialization for all providers."""
    # Create service instances
    llm_provider_service = LLMProviderService(db_session)
    llm_parameters_service = LLMParametersService(db_session)
    prompt_template_service = PromptTemplateService(db_session)

    # Initialize providers using the `initialize_providers` method
    initialized_providers = llm_provider_service.initialize_providers(raise_on_error=True)

    # Verify that the providers were initialized
    assert len(initialized_providers) > 0

    # Initialize provider
    provider_class(llm_provider_service, llm_parameters_service, prompt_template_service)

    # Simulate parameter and template creation
    params: LLMParametersOutput = llm_parameters_service.create_parameters(test_parameters[provider_key])
    template: PromptTemplateOutput = prompt_template_service.create_template(test_templates[provider_key])

    # Verify provider state
    assert params is not None
    assert template is not None
  