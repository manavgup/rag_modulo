"""OpenAI provider implementation for text generation and embeddings."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import TYPE_CHECKING, Any

from openai import AsyncOpenAI, OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from core.custom_exceptions import LLMProviderError, NotFoundError, ValidationError
from core.logging_utils import get_logger
from rag_solution.schemas.llm_model_schema import ModelType
from rag_solution.schemas.llm_usage_schema import LLMUsage, ServiceType
from rag_solution.schemas.structured_output_schema import (
    StructuredAnswer,
    StructuredOutputConfig,
)

from .base import LLMBase

if TYPE_CHECKING:
    from collections.abc import Generator, Sequence

    from pydantic import UUID4

    from rag_solution.schemas.llm_parameters_schema import LLMParametersInput
    from rag_solution.schemas.prompt_template_schema import PromptTemplateBase
    from vectordbs.data_types import EmbeddingsList

logger = get_logger("llm.providers.openai")


class OpenAILLM(LLMBase):
    """OpenAI provider implementation using OpenAI API."""

    def initialize_client(self) -> None:
        """Initialize OpenAI client."""
        try:
            provider = self._get_provider_config("openai")
            self._provider = provider

            self.client = OpenAI(
                api_key=str(provider.api_key), organization=provider.org_id, base_url=provider.base_url
            )
            self.async_client = AsyncOpenAI(
                api_key=str(provider.api_key), organization=provider.org_id, base_url=provider.base_url
            )

            self._models = self.llm_model_service.get_models_by_provider(provider.id)
            self._initialize_default_models()

        except Exception as e:
            raise LLMProviderError(
                provider="openai", error_type="initialization_failed", message=f"Failed to initialize client: {e!s}"
            ) from e

    def _initialize_default_models(self) -> None:
        """Initialize default models for generation and embeddings."""
        self._default_model = next(
            (m for m in self._models if m.is_default and m.model_type == ModelType.GENERATION), None
        )
        self._default_embedding_model = next(
            (m for m in self._models if m.is_default and m.model_type == ModelType.EMBEDDING), None
        )

        if not self._default_model:
            logger.warning("No default model configured, using gpt-3.5-turbo")
            self._default_model_id = "gpt-3.5-turbo"
        else:
            self._default_model_id = self._default_model.model_id

        if not self._default_embedding_model:
            logger.warning("No default embedding model configured, using text-embedding-ada-002")
            self._default_embedding_model_id = "text-embedding-ada-002"
        else:
            self._default_embedding_model_id = self._default_embedding_model.model_id

    def _get_generation_params(
        self, user_id: UUID4, model_parameters: LLMParametersInput | None = None
    ) -> dict[str, Any]:
        """Get validated generation parameters."""
        params = model_parameters or self.llm_parameters_service.get_latest_or_default_parameters(user_id)

        return {
            "max_tokens": params.max_new_tokens if params else 150,
            "temperature": params.temperature if params else 0.7,
            "top_p": params.top_p if params else 1.0,
        }

    def generate_text(
        self,
        user_id: UUID4,
        prompt: str | Sequence[str],
        model_parameters: LLMParametersInput | None = None,
        template: PromptTemplateBase | None = None,
        variables: dict[str, Any] | None = None,
    ) -> str | list[str]:
        """Generate text using OpenAI model."""
        try:
            self._ensure_client()
            model_id = self._model_id or self._default_model_id
            generation_params = self._get_generation_params(user_id, model_parameters)

            # Handle batch generation
            if isinstance(prompt, list):
                formatted_prompts = [self._format_prompt(str(p), template, variables) for p in prompt]
                # Use asyncio for concurrent processing
                result = asyncio.run(self._generate_batch(model_id, formatted_prompts, generation_params))
                return result
            else:
                formatted_prompt = self._format_prompt(str(prompt), template, variables)
                response = self.client.chat.completions.create(  # type: ignore[union-attr]
                    model=model_id, messages=[{"role": "user", "content": formatted_prompt}], **generation_params
                )
                content: str | None = response.choices[0].message.content
                if content is None:
                    raise LLMProviderError(
                        provider="openai", error_type="generation_failed", message="OpenAI returned empty content"
                    )
                return content.strip()

        except (ValidationError, NotFoundError) as e:
            raise LLMProviderError(
                provider="openai",
                error_type="invalid_template" if isinstance(e, ValidationError) else "template_not_found",
                message=str(e),
            ) from e
        except Exception as e:
            raise LLMProviderError(
                provider="openai", error_type="generation_failed", message=f"Failed to generate text: {e!s}"
            ) from e

    def _format_prompt(
        self, prompt: str, template: PromptTemplateBase | None = None, variables: dict[str, Any] | None = None
    ) -> str:
        """Format a prompt using a template and variables."""
        if template:
            vars_dict = dict(variables or {})
            vars_dict["prompt"] = prompt
            return self.prompt_template_service.format_prompt_with_template(template, vars_dict)
        return prompt

    async def _generate_batch(self, model_id: str, prompts: list[str], generation_params: dict[str, Any]) -> list[str]:
        """Generate text for multiple prompts concurrently."""

        async def generate_single(prompt: str) -> str:
            response = await self.async_client.chat.completions.create(
                model=model_id, messages=[{"role": "user", "content": prompt}], **generation_params
            )
            content: str | None = response.choices[0].message.content
            if content is None:
                raise LLMProviderError(
                    provider="openai", error_type="generation_failed", message="OpenAI returned empty content"
                )
            return content.strip()

        # Process prompts concurrently with a semaphore to limit concurrency
        semaphore = asyncio.Semaphore(10)  # Limit concurrent requests

        async def bounded_generate(prompt: str) -> str:
            async with semaphore:
                return await generate_single(prompt)

        tasks = [bounded_generate(prompt) for prompt in prompts]
        result = await asyncio.gather(*tasks)
        return result

    @retry(
        wait=wait_exponential(multiplier=1, min=1, max=30),
        stop=stop_after_attempt(3),
    )
    def generate_text_stream(
        self,
        user_id: UUID4,
        prompt: str,
        model_parameters: LLMParametersInput | None = None,
        template: PromptTemplateBase | None = None,
        variables: dict[str, Any] | None = None,
    ) -> Generator[str, None, None]:
        """Generate text in streaming mode."""
        try:
            self._ensure_client()
            model_id = self._model_id or self._default_model_id
            generation_params = self._get_generation_params(user_id, model_parameters)
            generation_params["stream"] = True

            formatted_prompt = self._format_prompt(prompt, template, variables)
            stream = self.client.chat.completions.create(  # type: ignore[union-attr]
                model=model_id, messages=[{"role": "user", "content": formatted_prompt}], **generation_params
            )

            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except (ValidationError, NotFoundError) as e:
            raise LLMProviderError(
                provider="openai",
                error_type="invalid_template" if isinstance(e, ValidationError) else "template_not_found",
                message=str(e),
            ) from e
        except Exception as e:
            raise LLMProviderError(
                provider="openai", error_type="streaming_failed", message=f"Failed to generate streaming text: {e!s}"
            ) from e

    def get_embeddings(self, texts: str | Sequence[str]) -> EmbeddingsList:
        """Generate embeddings for texts."""
        try:
            self._ensure_client()

            if isinstance(texts, str):
                texts = [texts]

            # OpenAI embeddings API already handles batching efficiently
            response = self.client.embeddings.create(model=self._default_embedding_model_id, input=texts)  # type: ignore[union-attr]
            result = [data.embedding for data in response.data]
            return result

        except LLMProviderError:
            raise
        except Exception as e:
            raise LLMProviderError(
                provider="openai", error_type="embeddings_failed", message=f"Failed to generate embeddings: {e!s}"
            ) from e

    def generate_text_with_usage(
        self,
        user_id: UUID4,
        prompt: str | Sequence[str],
        service_type: ServiceType,
        model_parameters: LLMParametersInput | None = None,
        template: PromptTemplateBase | None = None,
        variables: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> tuple[str | list[str], LLMUsage]:
        """Generate text and return both result and accurate usage information from OpenAI API."""
        try:
            self._ensure_client()
            model_id = self._model_id or self._default_model_id
            generation_params = self._get_generation_params(user_id, model_parameters)

            # For single prompt, get actual usage from API response
            if not isinstance(prompt, list):
                formatted_prompt = self._format_prompt(str(prompt), template, variables)
                response = self.client.chat.completions.create(  # type: ignore[union-attr]
                    model=model_id, messages=[{"role": "user", "content": formatted_prompt}], **generation_params
                )
                content: str | None = response.choices[0].message.content
                if content is None:
                    raise LLMProviderError(
                        provider="openai", error_type="generation_failed", message="OpenAI returned empty content"
                    )

                # Create usage record with actual API data
                usage = LLMUsage(
                    prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
                    completion_tokens=response.usage.completion_tokens if response.usage else 0,
                    total_tokens=response.usage.total_tokens if response.usage else 0,
                    model_name=model_id,
                    service_type=service_type,
                    timestamp=datetime.now(),
                    user_id=str(user_id),
                    session_id=session_id,
                )

                self.track_usage(usage)
                return content.strip(), usage
            else:
                # For batch, use default implementation since it's complex
                return super().generate_text_with_usage(
                    user_id, prompt, service_type, model_parameters, template, variables, session_id
                )

        except (ValidationError, NotFoundError) as e:
            raise LLMProviderError(
                provider="openai",
                error_type="invalid_template" if isinstance(e, ValidationError) else "template_not_found",
                message=str(e),
            ) from e
        except Exception as e:
            raise LLMProviderError(
                provider="openai", error_type="generation_failed", message=f"Failed to generate text: {e!s}"
            ) from e

    def generate_structured_output(
        self,
        user_id: UUID4,
        prompt: str,
        context_documents: list[dict[str, Any]],
        config: StructuredOutputConfig | None = None,
        model_parameters: LLMParametersInput | None = None,
    ) -> tuple[StructuredAnswer, LLMUsage]:
        """Generate structured output using OpenAI's native JSON schema mode.

        Args:
            user_id: UUID4 of the user making the request
            prompt: The user's query/prompt
            context_documents: List of retrieved documents with metadata
            config: Structured output configuration
            model_parameters: Optional LLM parameters

        Returns:
            Tuple of (StructuredAnswer, LLMUsage)

        Raises:
            LLMProviderError: If generation fails or response is invalid
        """
        try:
            self._ensure_client()
            model_id = self._model_id or self._default_model_id
            generation_params = self._get_generation_params(user_id, model_parameters)

            # Use default config if not provided
            if config is None:
                config = StructuredOutputConfig(enabled=True)

            # Build the prompt with context
            formatted_prompt = self._build_structured_prompt(prompt, context_documents, config)

            # Define JSON schema for OpenAI's structured output
            json_schema = self._get_openai_json_schema(config)

            # Call OpenAI with JSON schema mode
            response = self.client.chat.completions.create(  # type: ignore[union-attr]
                model=model_id,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a helpful assistant that provides structured answers with citations. "
                            "Always cite your sources using the provided document references."
                        ),
                    },
                    {"role": "user", "content": formatted_prompt},
                ],
                response_format={"type": "json_schema", "json_schema": json_schema},
                **generation_params,
            )

            # Parse response content
            content: str | None = response.choices[0].message.content
            if not content:
                raise LLMProviderError(
                    provider="openai", error_type="generation_failed", message="OpenAI returned empty content"
                )

            # Parse JSON response
            try:
                response_data = json.loads(content)
                structured_answer = StructuredAnswer(**response_data)
            except (json.JSONDecodeError, ValidationError) as e:
                raise LLMProviderError(
                    provider="openai",
                    error_type="invalid_response",
                    message=f"Failed to parse structured output: {e!s}",
                ) from e

            # Create usage record
            usage = LLMUsage(
                prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
                completion_tokens=response.usage.completion_tokens if response.usage else 0,
                total_tokens=response.usage.total_tokens if response.usage else 0,
                model_name=model_id,
                service_type=ServiceType.GENERATION,
                timestamp=datetime.now(),
                user_id=str(user_id),
            )

            self.track_usage(usage)
            return structured_answer, usage

        except LLMProviderError:
            raise
        except Exception as e:
            raise LLMProviderError(
                provider="openai",
                error_type="generation_failed",
                message=f"Failed to generate structured output: {e!s}",
            ) from e

    def _build_structured_prompt(
        self, prompt: str, context_documents: list[dict[str, Any]], config: StructuredOutputConfig
    ) -> str:
        """Build a prompt that includes context documents for structured output.

        Args:
            prompt: User's query
            context_documents: Retrieved documents with metadata
            config: Structured output configuration

        Returns:
            Formatted prompt with context
        """
        # Format context documents with configurable truncation
        def truncate_content(content: str, max_length: int) -> str:
            """Truncate content with ellipsis indicator."""
            if len(content) <= max_length:
                return content
            return content[:max_length] + "..."

        context_text = "\n\n".join(
            [
                f"Document {i + 1} (ID: {doc.get('id', 'unknown')}):\n"
                f"Title: {doc.get('title', 'Untitled')}\n"
                f"Content: {truncate_content(doc.get('content', ''), config.max_context_per_doc)}"
                for i, doc in enumerate(context_documents[: config.max_citations])
            ]
        )

        # Build final prompt
        prompt_parts = [
            f"Question: {prompt}",
            "\nContext Documents:",
            context_text,
            "\nPlease provide a structured answer with:",
            "1. A clear, concise answer to the question",
            "2. A confidence score (0.0-1.0) based on the quality and relevance of the sources",
            "3. Citations to specific documents that support your answer",
        ]

        if config.include_reasoning:
            prompt_parts.append("4. Step-by-step reasoning showing how you arrived at your answer")

        return "\n".join(prompt_parts)

    def _get_openai_json_schema(self, config: StructuredOutputConfig) -> dict[str, Any]:
        """Get OpenAI-compatible JSON schema for structured output.

        Args:
            config: Structured output configuration

        Returns:
            JSON schema dictionary for OpenAI API
        """
        schema = {
            "name": "structured_answer",
            "strict": config.validation_strict,
            "schema": {
                "type": "object",
                "properties": {
                    "answer": {"type": "string", "description": "The main answer text"},
                    "confidence": {
                        "type": "number",
                        "description": "Confidence score between 0.0 and 1.0",
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                    "citations": {
                        "type": "array",
                        "description": "List of citations supporting the answer",
                        "items": {
                            "type": "object",
                            "properties": {
                                "document_id": {"type": "string", "description": "UUID of source document"},
                                "title": {"type": "string", "description": "Document title"},
                                "excerpt": {"type": "string", "description": "Relevant excerpt"},
                                "page_number": {"type": ["integer", "null"], "description": "Page number"},
                                "relevance_score": {
                                    "type": "number",
                                    "description": "Relevance score",
                                    "minimum": 0.0,
                                    "maximum": 1.0,
                                },
                                "chunk_id": {"type": ["string", "null"], "description": "Chunk identifier"},
                            },
                            "required": ["document_id", "title", "excerpt", "relevance_score"],
                            "additionalProperties": False,
                        },
                    },
                    "format_type": {
                        "type": "string",
                        "description": "Answer format type",
                        "enum": ["standard", "cot_reasoning", "comparative", "summary"],
                    },
                    "metadata": {"type": "object", "description": "Additional metadata"},
                },
                "required": ["answer", "confidence", "citations", "format_type"],
                "additionalProperties": False,
            },
        }

        # Add reasoning_steps if requested
        if config.include_reasoning:
            schema["schema"]["properties"]["reasoning_steps"] = {
                "type": "array",
                "description": "Step-by-step reasoning process",
                "items": {
                    "type": "object",
                    "properties": {
                        "step_number": {"type": "integer", "description": "Step number", "minimum": 1},
                        "thought": {"type": "string", "description": "Reasoning or analysis"},
                        "conclusion": {"type": "string", "description": "Conclusion from this step"},
                        "citations": {
                            "type": "array",
                            "description": "Citations for this step",
                            "items": {"$ref": "#/properties/citations/items"},
                        },
                    },
                    "required": ["step_number", "thought", "conclusion"],
                    "additionalProperties": False,
                },
            }

        return schema

    def close(self) -> None:
        """Clean up provider resources."""
        if hasattr(self, "client") and self.client:
            self.client.close()
        if hasattr(self, "async_client") and self.async_client:
            # Note: async_client.close() returns a coroutine, but we can't await in sync method
            # The async client will be cleaned up when the event loop is closed
            pass
        super().close()
