"""Tokenization utilities for accurate token counting across different LLM providers.

This module provides model-specific tokenizers for accurate token counting,
supporting OpenAI (via tiktoken), Anthropic, and IBM WatsonX models.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


class TokenizationUtils:
    """Utility class for model-specific tokenization and token counting."""

    # Model to tokenizer mapping
    MODEL_TOKENIZERS: dict[str, str] = {
        # OpenAI models
        "gpt-4": "cl100k_base",
        "gpt-4-32k": "cl100k_base",
        "gpt-4-0314": "cl100k_base",
        "gpt-4-32k-0314": "cl100k_base",
        "gpt-4-0613": "cl100k_base",
        "gpt-4-32k-0613": "cl100k_base",
        "gpt-3.5-turbo": "cl100k_base",
        "gpt-3.5-turbo-16k": "cl100k_base",
        "gpt-3.5-turbo-0301": "cl100k_base",
        "gpt-3.5-turbo-0613": "cl100k_base",
        "gpt-3.5-turbo-16k-0613": "cl100k_base",
        "text-davinci-003": "p50k_base",
        "text-davinci-002": "p50k_base",
        "text-davinci-001": "r50k_base",
        "text-curie-001": "r50k_base",
        "text-babbage-001": "r50k_base",
        "text-ada-001": "r50k_base",
        "davinci": "r50k_base",
        "curie": "r50k_base",
        "babbage": "r50k_base",
        "ada": "r50k_base",
        # Embedding models
        "text-embedding-ada-002": "cl100k_base",
        "text-embedding-3-small": "cl100k_base",
        "text-embedding-3-large": "cl100k_base",
    }

    # Model context windows
    MODEL_CONTEXT_WINDOWS: dict[str, int] = {
        # OpenAI models
        "gpt-4": 8192,
        "gpt-4-32k": 32768,
        "gpt-4-0314": 8192,
        "gpt-4-32k-0314": 32768,
        "gpt-4-0613": 8192,
        "gpt-4-32k-0613": 32768,
        "gpt-3.5-turbo": 4096,
        "gpt-3.5-turbo-16k": 16384,
        "gpt-3.5-turbo-0301": 4096,
        "gpt-3.5-turbo-0613": 4096,
        "gpt-3.5-turbo-16k-0613": 16384,
        "text-davinci-003": 4097,
        "text-davinci-002": 4097,
        # Anthropic models
        "claude-3-opus": 200000,
        "claude-3-sonnet": 200000,
        "claude-3-haiku": 200000,
        "claude-2.1": 200000,
        "claude-2": 100000,
        "claude-instant-1.2": 100000,
        # IBM WatsonX models
        "ibm/granite-3-3-8b-instruct": 8192,
        "ibm/granite-3-8b-instruct": 8192,
        "ibm/granite-13b-chat-v2": 8192,
        "ibm/granite-20b-multilingual": 8192,
        "meta-llama/llama-3-70b-instruct": 8192,
        "meta-llama/llama-3-8b-instruct": 8192,
        "mistralai/mixtral-8x7b-instruct-v01": 32768,
    }

    @classmethod
    @lru_cache(maxsize=128)
    def get_tokenizer(cls, model_name: str) -> Callable[[str], list[int]] | None:
        """Get the appropriate tokenizer for a model.

        Args:
            model_name: Name of the model

        Returns:
            Tokenizer function or None if not available
        """
        # Try tiktoken for OpenAI models
        if model_name in cls.MODEL_TOKENIZERS:
            try:
                import tiktoken

                encoding_name = cls.MODEL_TOKENIZERS[model_name]
                encoding = tiktoken.get_encoding(encoding_name)
                return encoding.encode
            except ImportError:
                logger.warning("tiktoken not installed, falling back to estimation for %s", model_name)
                return None
            except Exception as e:
                logger.warning("Failed to get tiktoken encoding for %s: %s", model_name, e)
                return None

        # Try transformers for other models
        if "granite" in model_name.lower() or "llama" in model_name.lower() or "mixtral" in model_name.lower():
            try:
                from transformers import AutoTokenizer

                # Use a representative tokenizer for each family
                if "granite" in model_name.lower():
                    tokenizer = AutoTokenizer.from_pretrained("ibm-granite/granite-3b-code-base", use_fast=True)
                elif "llama" in model_name.lower():
                    tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-2-7b-hf", use_fast=True)
                elif "mixtral" in model_name.lower():
                    tokenizer = AutoTokenizer.from_pretrained("mistralai/Mistral-7B-v0.1", use_fast=True)
                else:
                    return None

                return lambda text: tokenizer.encode(text, add_special_tokens=True)
            except ImportError:
                logger.warning("transformers not installed, falling back to estimation for %s", model_name)
                return None
            except Exception as e:
                logger.warning("Failed to get transformers tokenizer for %s: %s", model_name, e)
                return None

        # For Anthropic models, use character-based estimation
        # Anthropic doesn't provide a public tokenizer
        if "claude" in model_name.lower():
            return None

        return None

    @classmethod
    def count_tokens(cls, text: str, model_name: str) -> int:
        """Count tokens for a given text and model.

        Args:
            text: Text to tokenize
            model_name: Name of the model

        Returns:
            Token count
        """
        tokenizer = cls.get_tokenizer(model_name)
        if tokenizer:
            try:
                tokens = tokenizer(text)
                return len(tokens)
            except Exception as e:
                logger.warning("Tokenization failed for %s: %s", model_name, e)

        # Fallback to estimation
        return cls.estimate_tokens(text, model_name)

    @classmethod
    def estimate_tokens(cls, text: str, model_name: str | None = None) -> int:
        """Estimate token count when exact tokenization is not available.

        Uses model-specific heuristics for better accuracy.

        Args:
            text: Text to estimate tokens for
            model_name: Optional model name for model-specific estimation

        Returns:
            Estimated token count
        """
        if not text:
            return 0

        # Model-specific estimations
        if model_name:
            if "claude" in model_name.lower():
                # Claude tends to have slightly different tokenization
                # Anthropic models average ~3.5 characters per token
                return max(1, len(text) // 3.5)
            elif "granite" in model_name.lower() or "llama" in model_name.lower():
                # These models tend to have more aggressive tokenization
                # Average ~3.8 characters per token
                return max(1, int(len(text) // 3.8))
            elif "gpt" in model_name.lower():
                # GPT models average ~4 characters per token for English
                return max(1, len(text) // 4)

        # Default estimation: ~4 characters per token (OpenAI's rough guideline)
        # This is a reasonable default for English text
        base_estimate = len(text) // 4

        # Adjust for complexity
        # Count special characters and punctuation
        special_chars = sum(1 for c in text if not c.isalnum() and not c.isspace())
        adjustment = special_chars // 10  # Roughly 10 special chars add 1 token

        return max(1, base_estimate + adjustment)

    @classmethod
    def get_context_window(cls, model_name: str) -> int:
        """Get the context window size for a model.

        Args:
            model_name: Name of the model

        Returns:
            Context window size in tokens
        """
        # Direct lookup
        if model_name in cls.MODEL_CONTEXT_WINDOWS:
            return cls.MODEL_CONTEXT_WINDOWS[model_name]

        # Pattern matching for model families
        model_lower = model_name.lower()

        # OpenAI GPT-4 variants
        if "gpt-4" in model_lower:
            if "32k" in model_lower:
                return 32768
            elif "turbo" in model_lower:
                return 128000  # GPT-4 Turbo
            else:
                return 8192

        # OpenAI GPT-3.5 variants
        if "gpt-3.5" in model_lower:
            if "16k" in model_lower:
                return 16384
            else:
                return 4096

        # Anthropic Claude variants
        if "claude" in model_lower:
            if "claude-3" in model_lower:
                return 200000
            elif "claude-2" in model_lower:
                return 100000 if "claude-2.1" not in model_lower else 200000
            else:
                return 100000

        # IBM Granite models
        if "granite" in model_lower:
            return 8192

        # Meta Llama models
        if "llama" in model_lower:
            if "llama-3" in model_lower:
                return 8192
            else:
                return 4096

        # Mistral/Mixtral models
        if "mistral" in model_lower or "mixtral" in model_lower:
            if "mixtral" in model_lower:
                return 32768
            else:
                return 8192

        # Default fallback
        logger.warning("Unknown model %s, using default context window of 4096", model_name)
        return 4096

    @classmethod
    def truncate_to_token_limit(cls, text: str, model_name: str, max_tokens: int | None = None) -> str:
        """Truncate text to fit within token limit.

        Args:
            text: Text to truncate
            model_name: Name of the model
            max_tokens: Maximum number of tokens (uses model's context window if not specified)

        Returns:
            Truncated text
        """
        if not max_tokens:
            max_tokens = cls.get_context_window(model_name)

        current_tokens = cls.count_tokens(text, model_name)
        if current_tokens <= max_tokens:
            return text

        # Binary search for the right truncation point
        left, right = 0, len(text)
        result = ""

        while left <= right:
            mid = (left + right) // 2
            truncated = text[:mid]
            tokens = cls.count_tokens(truncated, model_name)

            if tokens <= max_tokens:
                result = truncated
                left = mid + 1
            else:
                right = mid - 1

        return result

    @classmethod
    def split_text_by_tokens(cls, text: str, model_name: str, chunk_size: int = 1000) -> list[str]:
        """Split text into chunks of approximately chunk_size tokens.

        Args:
            text: Text to split
            model_name: Name of the model
            chunk_size: Target size for each chunk in tokens

        Returns:
            List of text chunks
        """
        if not text:
            return []

        chunks = []
        current_chunk = ""
        current_tokens = 0

        # Split by sentences for better coherence
        sentences = text.replace(".", ". ").replace("!", "! ").replace("?", "? ").split()

        for sentence in sentences:
            sentence_tokens = cls.count_tokens(sentence, model_name)

            if current_tokens + sentence_tokens > chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
                current_tokens = sentence_tokens
            else:
                current_chunk += " " + sentence
                current_tokens += sentence_tokens

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks