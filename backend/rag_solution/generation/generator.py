"""
DEPRECATED: This module is deprecated and will be removed in a future version.
A new CLI tool using the service layer architecture will be created to replace
this standalone utility. This module currently uses file-based configuration
(prompt_config.json) instead of the database-driven approach used by the main
application.
"""

import json
import logging
import os
import re
import warnings
from os.path import abspath, dirname
from typing import Any

from core.config import settings
from vectordbs.utils.watsonx import generate_text

logger = logging.getLogger(__name__)

warnings.warn(
    "The generator.py module is deprecated and will be removed in a future version. "
    "A new CLI tool using the service layer architecture will replace this utility.",
    DeprecationWarning,
    stacklevel=2,
)


class PromptTemplate:
    def __init__(self, config: dict[str, str]):
        self.system_prompt = config["system_prompt"]
        self.context_prefix = config["context_prefix"]
        self.query_prefix = config["query_prefix"]
        self.answer_prefix = config["answer_prefix"]

    def format(self, query: str, context: str) -> str:
        return f"{self.system_prompt}\n\n{self.context_prefix}\n{context}\n\n{self.query_prefix}\n{query}\n\n{self.answer_prefix}"


class BaseGenerator:
    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.prompt_template = self._load_prompt_template()
        self.max_tokens = self.config.get("max_tokens", 2048)

    def _load_prompt_template(self) -> PromptTemplate:
        prompt_config_path = f"{abspath(dirname(dirname(__file__)))}/config/prompt_config.json"
        try:
            with open(prompt_config_path) as f:
                prompt_config = json.load(f)

            logger.info(f"Config in BaseGenerator: {self.config}")
            logger.info(f"Prompt type: {self.config.get('type')}")

            prompt_type = self.config.get("type")
            if prompt_type not in prompt_config:
                raise ValueError(f"Invalid prompt type: {prompt_type}")

            return PromptTemplate(prompt_config[self.config["type"]])
        except (FileNotFoundError, KeyError) as e:
            logger.error(f"Error loading prompt template: {e}")
            raise ValueError(f"Error loading prompt template: {e}") from e

    def approximate_token_count(self, text: str) -> int:
        # This is a simple approximation. Adjust as needed for your specific use case.
        return len(re.findall(r"\w+", text))

    def truncate_context(self, context: str, query: str) -> str:
        query_tokens = self.approximate_token_count(query)
        prompt_template_tokens = self.approximate_token_count(self.prompt_template.format("", ""))
        available_tokens = (
            self.max_tokens - query_tokens - prompt_template_tokens - 50
        )  # Reserve some tokens for safety

        context_words = context.split()
        if len(context_words) > available_tokens:
            truncated_context = " ".join(context_words[:available_tokens])
            logger.info(f"Context truncated from {len(context_words)} to {available_tokens} tokens")
            return truncated_context
        return context

    def generate(self, prompt: str | list[str], context: str | None = None, **kwargs: Any) -> str | list[str]:
        raise NotImplementedError

    def generate_stream(self, prompt: str | list[str], context: str | None = None, **kwargs: Any) -> str | list[str]:
        raise NotImplementedError


class WatsonxGenerator(BaseGenerator):
    def __init__(self, config: dict[str, Any]):
        if not isinstance(config, dict):
            raise TypeError(f"Expected config to be a dictionary, but got {type(config).__name__}")

        super().__init__(config)
        self.model_name = config.get("model_name", settings.rag_llm)

    def generate(self, prompt: str | list[str], context: str | None = None, **kwargs: Any) -> str | list[str]:  # noqa: ARG002
        """Generate text using the language model.

        Args:
            query: The query text
            context: Either a single context string or list of prompts for batch processing
            **kwargs: Additional generation parameters

        Returns:
            Generated text(s)
        """
        try:
            return generate_text(
                prompt=prompt,
                concurrency_limit=kwargs.get("concurrency_limit", 10),
                params=kwargs.get("params", self.config.get("default_params")),
            )
        except Exception as e:
            logger.error("Error generating: %s", str(e))
            raise

    def generate_stream(self, prompt: str | list[str], context: str | None = None, **kwargs: Any) -> str | list[str]:
        """Generate text stream using the language model.

        Note: This method is deprecated and will be removed in a future version.
        The streaming functionality has been moved to the service layer.
        """
        # For backward compatibility, return the first result as a string
        if isinstance(prompt, list):
            prompt = prompt[0] if prompt else ""

        truncated_context = self.truncate_context(context or "", prompt)
        formatted_prompt = self.prompt_template.format(query=prompt, context=truncated_context)
        try:
            result = generate_text(formatted_prompt, **kwargs)
            return result
        except Exception as e:
            logger.error(f"Error generating text stream: {e}")
            raise


class OpenAIGenerator(BaseGenerator):
    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.model_name = config.get("model_name", "gpt-3.5-turbo")
        import openai

        openai.api_key = os.getenv("OPENAI_API_KEY")

    def generate(self, prompt: str | list[str], context: str | None = None, **kwargs: Any) -> str | list[str]:
        """Generate text using OpenAI.

        Note: This method is deprecated and will be removed in a future version.
        """

        if isinstance(prompt, list):
            prompt = prompt[0] if prompt else ""

        truncated_context = self.truncate_context(context or "", prompt)
        formatted_prompt = self.prompt_template.format(query=prompt, context=truncated_context)
        try:
            # Use the correct OpenAI client API
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            response = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self.prompt_template.system_prompt},
                    {"role": "user", "content": formatted_prompt},
                ],
                **kwargs,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"Error generating text with OpenAI: {e}")
            raise

    def generate_stream(self, prompt: str | list[str], context: str | None = None, **kwargs: Any) -> str | list[str]:
        """Generate text stream using OpenAI.

        Note: This method is deprecated and will be removed in a future version.
        The streaming functionality has been moved to the service layer.
        """

        if isinstance(prompt, list):
            prompt = prompt[0] if prompt else ""

        truncated_context = self.truncate_context(context or "", prompt)
        formatted_prompt = self.prompt_template.format(query=prompt, context=truncated_context)
        try:
            # Use the correct OpenAI client API
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            response = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self.prompt_template.system_prompt},
                    {"role": "user", "content": formatted_prompt},
                ],
                **kwargs,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"Error generating text stream with OpenAI: {e}")
            raise


class AnthropicGenerator(BaseGenerator):
    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.model_name = config.get("model_name", "claude-2")
        import anthropic

        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.anthropic = anthropic

    def generate(self, prompt: str | list[str], context: str | None = None, **kwargs: Any) -> str | list[str]:
        """Generate text using Anthropic.

        Note: This method is deprecated and will be removed in a future version.
        """
        if isinstance(prompt, list):
            prompt = prompt[0] if prompt else ""

        truncated_context = self.truncate_context(context or "", prompt)
        formatted_prompt = self.prompt_template.format(query=prompt, context=truncated_context)
        try:
            response = self.client.completions.create(
                model=self.model_name,
                prompt=f"{self.anthropic.HUMAN_PROMPT} {formatted_prompt}{self.anthropic.AI_PROMPT}",
                **kwargs,
            )
            return response.completion or ""
        except Exception as e:
            logger.error(f"Error generating text with Anthropic: {e}")
            raise

    def generate_stream(self, prompt: str | list[str], context: str | None = None, **kwargs: Any) -> str | list[str]:
        """Generate text stream using Anthropic.

        Note: This method is deprecated and will be removed in a future version.
        The streaming functionality has been moved to the service layer.
        """
        if isinstance(prompt, list):
            prompt = prompt[0] if prompt else ""

        truncated_context = self.truncate_context(context or "", prompt)
        formatted_prompt = self.prompt_template.format(query=prompt, context=truncated_context)
        try:
            response = self.client.completions.create(
                model=self.model_name,
                prompt=f"{self.anthropic.HUMAN_PROMPT} {formatted_prompt}{self.anthropic.AI_PROMPT}",
                **kwargs,
            )
            return response.completion or ""
        except Exception as e:
            logger.error(f"Error generating text stream with Anthropic: {e}")
            raise


# Example usage
if __name__ == "__main__":
    config = {
        "type": "watsonx",
        "model_name": "flan-t5-xl",
        "max_tokens": 2048,
        "default_params": {"max_new_tokens": 100, "temperature": 0.7},
    }
    generator = WatsonxGenerator(config)
    query = "Explain the theory of relativity in simple terms."
    context = "Einstein's theory of relativity deals with space and time. It revolutionized our understanding of the universe."

    print("Non-streaming response:")
    response = generator.generate(query, context)
    print(response)

    print("\nStreaming response:")
    for chunk in generator.generate_stream(query, context):
        print(chunk, end="", flush=True)
    print()
