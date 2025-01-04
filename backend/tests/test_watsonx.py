"""Tests for WatsonX provider implementation."""

import pytest
from rag_solution.generation.providers.watsonx import WatsonXProvider
from core.custom_exceptions import LLMProviderError
from rag_solution.services.provider_config_service import ProviderConfigService
from vectordbs.data_types import EmbeddingsList
from core.config import settings
from rag_solution.schemas.provider_config_schema import ProviderConfig
from rag_solution.schemas.prompt_template_schema import PromptTemplateBase


@pytest.fixture
def provider_config_service(db_session):
    """Fixture for ProviderConfigService with actual settings."""
    return ProviderConfigService(db_session)


@pytest.fixture
def watsonx_provider(provider_config_service):
    """Fixture to initialize WatsonXProvider with actual settings."""
    provider = WatsonXProvider(provider_config_service)
    provider.initialize_client()
    return provider


@pytest.fixture
def test_template():
    """Fixture for test prompt template."""
    return PromptTemplateBase(
        name="test_template",
        provider="watsonx",
        system_prompt="You are a helpful AI assistant.",
        context_prefix="Context:\n",
        query_prefix="Question:\n",
        answer_prefix="Answer:\n",
        input_variables=["context", "question"],
        template_format="{question}"
    )


def test_get_embeddings_single_text(watsonx_provider):
    """Test generating embeddings for a single text input."""
    text = "This is a test sentence."
    result = watsonx_provider.get_embeddings(text)

    assert isinstance(result, list)
    assert len(result) > 0
    assert isinstance(result[0], list)  # Should be a list of floats
    assert all(isinstance(x, float) for x in result[0])  # All elements should be floats


def test_get_embeddings_multiple_texts(watsonx_provider):
    """Test generating embeddings for multiple text inputs."""
    texts = ["First sentence.", "Second sentence."]
    result = watsonx_provider.get_embeddings(texts)

    assert isinstance(result, list)
    assert len(result) == 2
    for embedding in result:
        assert isinstance(embedding, list)
        assert all(isinstance(x, float) for x in embedding)


def test_get_embeddings_no_model(watsonx_provider):
    """Test error when embeddings client is not initialized."""
    watsonx_provider.embeddings_client = None

    with pytest.raises(LLMProviderError) as exc_info:
        watsonx_provider.get_embeddings("Test text.")

    assert "Embeddings not configured" in str(exc_info.value)


def test_get_embeddings_empty_input(watsonx_provider):
    """Test empty input to embeddings."""
    result = watsonx_provider.get_embeddings("")

    assert isinstance(result, list)
    assert len(result) == 1  # Should still return an embedding for empty string
    assert isinstance(result[0], list)
    assert all(isinstance(x, float) for x in result[0])


def test_generate_text(watsonx_provider):
    """Test text generation."""
    prompt = "What is the capital of France?"
    result = watsonx_provider.generate_text(
        prompt=prompt,
        model_parameters=None
    )

    assert isinstance(result, str)
    assert len(result) > 0
    assert "Paris" in result.lower()


def test_generate_text_stream(watsonx_provider):
    """Test streaming text generation."""
    prompt = "What is the capital of France?"
    stream = watsonx_provider.generate_text_stream(
        prompt=prompt,
        model_parameters=None
    )

    chunks = []
    for chunk in stream:
        assert isinstance(chunk, str)
        chunks.append(chunk)

    assert len(chunks) > 0
    full_response = "".join(chunks)
    assert "Paris" in full_response.lower()


def test_generate_text_with_template(watsonx_provider, test_template):
    """Test text generation with prompt template."""
    result = watsonx_provider.generate_text(
        prompt="What is the capital of France?",
        model_parameters=None,
        template=test_template,
        variables={
            "context": "",
            "question": "What is the capital of France?"
        }
    )

    assert isinstance(result, str)
    assert len(result) > 0
    assert "Paris" in result.lower()


def test_generate_text_with_context(watsonx_provider, test_template):
    """Test text generation with context."""
    context = "Paris is the capital city of France. It is known for the Eiffel Tower."
    result = watsonx_provider.generate_text(
        prompt="What is the capital of France?",
        model_parameters=None,
        template=test_template,
        variables={
            "context": context,
            "question": "What is the capital of France?"
        }
    )

    assert isinstance(result, str)
    assert len(result) > 0
    assert "Paris" in result.lower()
    assert "capital" in result.lower()


def test_generate_text_missing_variables(watsonx_provider, test_template):
    """Test error when required variables are missing."""
    with pytest.raises(LLMProviderError) as exc_info:
        watsonx_provider.generate_text(
            prompt="What is the capital of France?",
            model_parameters=None,
            template=test_template,
            variables={}  # Missing required variables
        )

    assert "Missing required variables" in str(exc_info.value)


def test_generate_text_batch(watsonx_provider):
    """Test batch text generation."""
    prompts = [
        "What is the capital of France?",
        "What is the capital of Italy?"
    ]
    results = watsonx_provider.generate_text(
        prompt=prompts,
        model_parameters=None
    )

    assert isinstance(results, list)
    assert len(results) == 2
    assert all(isinstance(r, str) for r in results)
    assert "Paris" in results[0].lower()
    assert "Rome" in results[1].lower()
