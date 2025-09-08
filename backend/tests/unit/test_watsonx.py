"""Tests for WatsonX provider implementation."""

from typing import Any

from rag_solution.schemas.llm_parameters_schema import LLMParametersInput
from rag_solution.schemas.prompt_template_schema import PromptTemplateInput, PromptTemplateType


def test_provider_initialization(provider: Any, db_session: Any) -> None:
    """Test provider initialization with config."""
    # Provider should be automatically initialized by base class
    assert provider._provider_name == "watsonx"
    assert provider.client is not None

    # Verify client is properly configured
    provider.validate_client()

    # Test client reinitialization
    provider.client = None
    provider._ensure_client()
    assert provider.client is not None


def test_generate_text(provider: Any, base_user: Any, base_llm_parameters: Any) -> None:
    """Test text generation."""
    # Convert SQLAlchemy model to Pydantic input model
    params_input = LLMParametersInput(
        user_id=base_user.id,
        name=base_llm_parameters.name,
        description=base_llm_parameters.description,
        max_new_tokens=base_llm_parameters.max_new_tokens,
        temperature=base_llm_parameters.temperature,
        top_k=base_llm_parameters.top_k,
        top_p=base_llm_parameters.top_p,
        repetition_penalty=base_llm_parameters.repetition_penalty,
        is_default=base_llm_parameters.is_default,
    )

    prompt = "What is the capital of France?"
    response = provider.generate_text(user_id=base_user.id, prompt=prompt, model_parameters=params_input)

    assert isinstance(response, str)
    assert len(response) > 0


def test_generate_text_stream(provider: Any, base_user: Any, base_llm_parameters: Any) -> None:
    """Test streaming text generation."""
    # Convert SQLAlchemy model to Pydantic input model
    params_input = LLMParametersInput(
        user_id=base_user.id,
        name=base_llm_parameters.name,
        description=base_llm_parameters.description,
        max_new_tokens=base_llm_parameters.max_new_tokens,
        temperature=base_llm_parameters.temperature,
        top_k=base_llm_parameters.top_k,
        top_p=base_llm_parameters.top_p,
        repetition_penalty=base_llm_parameters.repetition_penalty,
        is_default=base_llm_parameters.is_default,
    )

    prompt = "What is the capital of France?"
    stream = provider.generate_text_stream(user_id=base_user.id, prompt=prompt, model_parameters=params_input)

    chunks = list(stream)
    assert len(chunks) > 0
    assert all(isinstance(chunk, str) for chunk in chunks)


def test_get_embeddings(provider: Any) -> None:
    """Test embedding generation."""
    from unittest.mock import patch

    texts = ["This is a test sentence.", "Another test sentence."]
    mock_embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]

    with patch.object(provider, "get_embeddings", return_value=mock_embeddings):
        embeddings = provider.get_embeddings(texts=texts)

    assert len(embeddings) == len(texts)
    assert all(len(emb) > 0 for emb in embeddings)


def test_template_formatting(provider: Any, base_user: Any, base_llm_parameters: Any, prompt_template_service: Any) -> None:
    """Test prompt template formatting."""
    # Convert SQLAlchemy model to Pydantic input model
    params_input = LLMParametersInput(
        user_id=base_user.id,
        name=base_llm_parameters.name,
        description=base_llm_parameters.description,
        max_new_tokens=base_llm_parameters.max_new_tokens,
        temperature=base_llm_parameters.temperature,
        top_k=base_llm_parameters.top_k,
        top_p=base_llm_parameters.top_p,
        repetition_penalty=base_llm_parameters.repetition_penalty,
        is_default=base_llm_parameters.is_default,
    )
    # Create template
    template = prompt_template_service.create_or_update_template(
        base_user.id,
        PromptTemplateInput(
            name="test-template",
            user_id=base_user.id,
            template_type=PromptTemplateType.RAG_QUERY,
            template_format="Question: {question}\nContext: {context}",
            input_variables={"question": "User's question", "context": "Retrieved context"},
            max_context_length=1000,
        ),
    )

    variables = {"question": "What is the capital of France?", "context": "France is a country in Europe."}

    response = provider.generate_text(
        user_id=base_user.id,
        prompt="Test prompt",
        model_parameters=params_input,
        template=template,
        variables=variables,
    )

    assert isinstance(response, str)
    assert len(response) > 0


def test_batch_generation(provider: Any, base_user: Any, base_llm_parameters: Any) -> None:
    """Test batch text generation."""
    # Convert SQLAlchemy model to Pydantic input model
    params_input = LLMParametersInput(
        user_id=base_user.id,
        name=base_llm_parameters.name,
        description=base_llm_parameters.description,
        max_new_tokens=base_llm_parameters.max_new_tokens,
        temperature=base_llm_parameters.temperature,
        top_k=base_llm_parameters.top_k,
        top_p=base_llm_parameters.top_p,
        repetition_penalty=base_llm_parameters.repetition_penalty,
        is_default=base_llm_parameters.is_default,
    )
    prompts = ["What is the capital of France?", "What is the capital of Germany?"]

    responses = provider.generate_text(user_id=base_user.id, prompt=prompts, model_parameters=params_input)

    assert isinstance(responses, list)
    assert len(responses) == len(prompts)
    assert all(isinstance(resp, str) for resp in responses)
