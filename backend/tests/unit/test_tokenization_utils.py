"""Unit tests for TokenizationUtils."""

import pytest

from rag_solution.utils.tokenization_utils import TokenizationUtils


class TestTokenizationUtils:
    """Test suite for TokenizationUtils class."""

    def test_estimate_tokens_default(self):
        """Test default token estimation."""
        text = "This is a test sentence with several words."
        tokens = TokenizationUtils.estimate_tokens(text)
        # ~44 characters, should be around 11 tokens
        assert 8 <= tokens <= 15

    def test_estimate_tokens_empty(self):
        """Test estimation with empty text."""
        assert TokenizationUtils.estimate_tokens("") == 0
        assert TokenizationUtils.estimate_tokens(" ") == 1

    def test_estimate_tokens_gpt_model(self):
        """Test GPT-specific estimation."""
        text = "This is a test sentence."
        tokens = TokenizationUtils.estimate_tokens(text, "gpt-3.5-turbo")
        # 24 characters / 4 = 6 tokens
        assert 5 <= tokens <= 8

    def test_estimate_tokens_claude_model(self):
        """Test Claude-specific estimation."""
        text = "This is a test sentence."
        tokens = TokenizationUtils.estimate_tokens(text, "claude-3-opus")
        # Claude uses ~3.5 chars per token: 24 / 3.5 = ~7 tokens
        assert 6 <= tokens <= 9

    def test_estimate_tokens_granite_model(self):
        """Test Granite-specific estimation."""
        text = "This is a test sentence."
        tokens = TokenizationUtils.estimate_tokens(text, "ibm/granite-3-8b-instruct")
        # Granite uses ~3.8 chars per token: 24 / 3.8 = ~6 tokens
        assert 5 <= tokens <= 8

    def test_get_context_window_gpt4(self):
        """Test GPT-4 context window."""
        assert TokenizationUtils.get_context_window("gpt-4") == 8192
        assert TokenizationUtils.get_context_window("gpt-4-32k") == 32768

    def test_get_context_window_gpt35(self):
        """Test GPT-3.5 context window."""
        assert TokenizationUtils.get_context_window("gpt-3.5-turbo") == 4096
        assert TokenizationUtils.get_context_window("gpt-3.5-turbo-16k") == 16384

    def test_get_context_window_claude(self):
        """Test Claude context windows."""
        assert TokenizationUtils.get_context_window("claude-3-opus") == 200000
        assert TokenizationUtils.get_context_window("claude-3-sonnet") == 200000
        assert TokenizationUtils.get_context_window("claude-2.1") == 200000
        assert TokenizationUtils.get_context_window("claude-2") == 100000

    def test_get_context_window_granite(self):
        """Test Granite context windows."""
        assert TokenizationUtils.get_context_window("ibm/granite-3-8b-instruct") == 8192
        assert TokenizationUtils.get_context_window("ibm/granite-13b-chat-v2") == 8192

    def test_get_context_window_llama(self):
        """Test Llama context windows."""
        assert TokenizationUtils.get_context_window("meta-llama/llama-3-70b-instruct") == 8192
        assert TokenizationUtils.get_context_window("meta-llama/llama-3-8b-instruct") == 8192

    def test_get_context_window_mixtral(self):
        """Test Mixtral context window."""
        assert TokenizationUtils.get_context_window("mistralai/mixtral-8x7b-instruct-v01") == 32768

    def test_get_context_window_unknown(self):
        """Test unknown model returns default."""
        assert TokenizationUtils.get_context_window("unknown-model-xyz") == 4096

    def test_truncate_to_token_limit(self):
        """Test text truncation to token limit."""
        text = "This is a very long sentence " * 100  # ~2900 characters
        model = "gpt-3.5-turbo"

        # Truncate to 100 tokens (~400 characters)
        truncated = TokenizationUtils.truncate_to_token_limit(text, model, max_tokens=100)

        # Check that truncated text has roughly the right token count
        token_count = TokenizationUtils.count_tokens(truncated, model)
        assert token_count <= 100
        assert len(truncated) < len(text)

    def test_split_text_by_tokens(self):
        """Test splitting text into token chunks."""
        text = " ".join([f"Sentence {i}." for i in range(100)])  # Generate 100 sentences
        model = "gpt-3.5-turbo"

        chunks = TokenizationUtils.split_text_by_tokens(text, model, chunk_size=50)

        # Should have multiple chunks
        assert len(chunks) > 1

        # Each chunk should be roughly 50 tokens or less
        for chunk in chunks:
            token_count = TokenizationUtils.count_tokens(chunk, model)
            assert token_count <= 60  # Allow some wiggle room

    def test_split_text_empty(self):
        """Test splitting empty text."""
        chunks = TokenizationUtils.split_text_by_tokens("", "gpt-3.5-turbo", 100)
        assert chunks == []

    def test_count_tokens_with_tiktoken(self):
        """Test token counting with tiktoken if available."""
        try:
            import tiktoken

            text = "Hello, world!"
            model = "gpt-3.5-turbo"

            # Should use tiktoken for accurate counting
            token_count = TokenizationUtils.count_tokens(text, model)
            assert token_count > 0
            assert token_count < 10  # "Hello, world!" should be ~4 tokens
        except ImportError:
            pytest.skip("tiktoken not installed")

    def test_count_tokens_fallback(self):
        """Test token counting falls back to estimation for unknown models."""
        text = "This is a test."
        model = "unknown-model-xyz"

        # Should fall back to estimation
        token_count = TokenizationUtils.count_tokens(text, model)
        assert token_count > 0
        assert token_count == TokenizationUtils.estimate_tokens(text, model)