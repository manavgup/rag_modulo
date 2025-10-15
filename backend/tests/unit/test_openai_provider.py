from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from rag_solution.generation.providers.openai import OpenAILLM
from rag_solution.schemas.llm_parameters_schema import LLMParametersInput


@pytest.fixture
def patched_openai_provider():
    with patch("rag_solution.generation.providers.openai.OpenAILLM.initialize_client", new_callable=MagicMock):
        mock_llm_model_service = MagicMock()
        mock_llm_parameters_service = MagicMock()
        mock_prompt_template_service = MagicMock()
        mock_llm_provider_service = MagicMock()

        provider = OpenAILLM(
            llm_model_service=mock_llm_model_service,
            llm_parameters_service=mock_llm_parameters_service,
            prompt_template_service=mock_prompt_template_service,
            llm_provider_service=mock_llm_provider_service,
        )
        provider.client = MagicMock()
        provider.async_client = MagicMock()
        provider._default_model_id = "gpt-3.5-turbo"
        provider._model_id = None

        mock_llm_parameters_service.get_latest_or_default_parameters.return_value = LLMParametersInput(
            name="test_parameters",
            user_id=uuid4(),
            max_new_tokens=150,
            temperature=0.7,
            top_p=1.0,
        )
        yield provider


@pytest.mark.unit
class TestOpenAILLM:
    def test_generate_text_stream_handles_key_error(self, patched_openai_provider):
        """
        Test that generate_text_stream correctly handles a stream with missing 'choices' key.
        This test is designed to fail initially (TDD Red).
        """
        provider = patched_openai_provider
        user_id = uuid4()
        prompt = "Hello, world!"

        # Mock the streaming response from the OpenAI client
        # This is a simplified representation of the stream chunks
        mock_stream = [
            MagicMock(),
            MagicMock(),
        ]
        # The first chunk has no 'choices'
        mock_stream[0].choices = []
        # The second chunk has the content
        mock_stream[1].choices = [MagicMock()]
        mock_stream[1].choices[0].delta.content = "Hello"

        provider.client.chat.completions.create.return_value = mock_stream

        # This should now run without raising an error
        result = list(provider.generate_text_stream(user_id=user_id, prompt=prompt))

        # Assert that the content from the second chunk is yielded
        assert result == ["Hello"]
