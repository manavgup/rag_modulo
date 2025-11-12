"""Anthropic provider implementation for text generation."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING, Any

import anthropic
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

logger = get_logger("llm.providers.anthropic")


class AnthropicLLM(LLMBase):
    """Anthropic provider implementation using Claude API."""

    def initialize_client(self) -> None:
        """Initialize Anthropic client."""
        try:
            provider = self._get_provider_config("anthropic")
            self._provider = provider

            self.client = anthropic.Anthropic(api_key=str(provider.api_key), base_url=provider.base_url)

            self._models = self.llm_model_service.get_models_by_provider(provider.id)
            self._initialize_default_model()

        except Exception as e:
            raise LLMProviderError(
                provider="anthropic",
                error_type="initialization_failed",
                message=f"Failed to initialize client: {e!s}",
            ) from e

    def _initialize_default_model(self) -> None:
        """Initialize default model for generation."""
        self._default_model = next(
            (m for m in self._models if m.is_default and m.model_type == ModelType.GENERATION), None
        )

        if not self._default_model:
            logger.warning("No default model configured, using claude-3-opus-20240229")
            self._default_model_id = "claude-3-opus-20240229"
        else:
            self._default_model_id = self._default_model.model_id

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
        """Generate text using Anthropic model."""
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
                response = self.client.messages.create(  # type: ignore[union-attr]
                    model=model_id, messages=[{"role": "user", "content": formatted_prompt}], **generation_params
                )
                content: str | None = response.content[0].text
                if content is None:
                    raise LLMProviderError(
                        provider="anthropic", error_type="generation_failed", message="Anthropic returned empty content"
                    )
                return content.strip()

        except (ValidationError, NotFoundError) as e:
            raise LLMProviderError(
                provider="anthropic",
                error_type="invalid_template" if isinstance(e, ValidationError) else "template_not_found",
                message=str(e),
            ) from e
        except Exception as e:
            raise LLMProviderError(
                provider="anthropic", error_type="generation_failed", message=f"Failed to generate text: {e!s}"
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
            # Create a new client for each request to avoid session conflicts
            async with anthropic.AsyncAnthropic(
                api_key=str(self._provider.api_key), base_url=self._provider.base_url
            ) as client:
                response = await client.messages.create(
                    model=model_id, messages=[{"role": "user", "content": prompt}], **generation_params
                )
                content: str | None = response.content[0].text
                if content is None:
                    raise LLMProviderError(
                        provider="anthropic", error_type="generation_failed", message="Anthropic returned empty content"
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
            stream = self.client.messages.create(  # type: ignore[union-attr]
                model=model_id, messages=[{"role": "user", "content": formatted_prompt}], **generation_params
            )

            for chunk in stream:
                if chunk.type == "content_block_delta" and chunk.delta.text:
                    yield chunk.delta.text

        except (ValidationError, NotFoundError) as e:
            raise LLMProviderError(
                provider="anthropic",
                error_type="invalid_template" if isinstance(e, ValidationError) else "template_not_found",
                message=str(e),
            ) from e
        except Exception as e:
            raise LLMProviderError(
                provider="anthropic",
                error_type="streaming_failed",
                message=f"Failed to generate streaming text: {e!s}",
            ) from e

    def get_embeddings(self, texts: str | Sequence[str]) -> EmbeddingsList:  # noqa: ARG002
        """Generate embeddings for texts.

        Raises:
            LLMProviderError: Anthropic does not provide embeddings
        """
        raise LLMProviderError(
            provider="anthropic", error_type="not_supported", message="Anthropic does not provide embeddings"
        )

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
        """Generate text and return both result and accurate usage information from Anthropic API."""
        try:
            self._ensure_client()
            model_id = self._model_id or self._default_model_id
            generation_params = self._get_generation_params(user_id, model_parameters)

            # For single prompt, get actual usage from API response
            if not isinstance(prompt, list):
                formatted_prompt = self._format_prompt(str(prompt), template, variables)
                response = self.client.messages.create(  # type: ignore[union-attr]
                    model=model_id, messages=[{"role": "user", "content": formatted_prompt}], **generation_params
                )
                content: str | None = response.content[0].text
                if content is None:
                    raise LLMProviderError(
                        provider="anthropic", error_type="generation_failed", message="Anthropic returned empty content"
                    )

                # Create usage record with actual API data
                usage = LLMUsage(
                    prompt_tokens=response.usage.input_tokens if response.usage else 0,
                    completion_tokens=response.usage.output_tokens if response.usage else 0,
                    total_tokens=(response.usage.input_tokens + response.usage.output_tokens) if response.usage else 0,
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
                provider="anthropic",
                error_type="invalid_template" if isinstance(e, ValidationError) else "template_not_found",
                message=str(e),
            ) from e
        except Exception as e:
            raise LLMProviderError(
                provider="anthropic", error_type="generation_failed", message=f"Failed to generate text: {e!s}"
            ) from e

    def generate_structured_output(
        self,
        user_id: UUID4,
        prompt: str,
        context_documents: list[dict[str, Any]],
        config: StructuredOutputConfig | None = None,
        model_parameters: LLMParametersInput | None = None,
        template: PromptTemplateBase | None = None,
    ) -> tuple[StructuredAnswer, LLMUsage]:
        """Generate structured output using Anthropic's tool use feature.

        Args:
            user_id: UUID4 of the user making the request
            prompt: The user's query/prompt
            context_documents: List of retrieved documents with metadata
            config: Structured output configuration
            model_parameters: Optional LLM parameters
            template: Optional prompt template for structured output

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
            formatted_prompt = self._build_structured_prompt(prompt, context_documents, config, template)

            # Define tool for structured output
            tool = self._get_anthropic_tool_schema(config)

            # Call Anthropic with tool use
            response = self.client.messages.create(  # type: ignore[union-attr]
                model=model_id,
                messages=[{"role": "user", "content": formatted_prompt}],
                tools=[tool],
                tool_choice={"type": "tool", "name": "provide_structured_answer"},
                **generation_params,
            )

            # Extract tool use from response
            tool_use = None
            for block in response.content:
                if block.type == "tool_use" and block.name == "provide_structured_answer":
                    tool_use = block
                    break

            if not tool_use:
                raise LLMProviderError(
                    provider="anthropic",
                    error_type="generation_failed",
                    message="No tool use found in Anthropic response",
                )

            # Parse tool input as structured answer
            try:
                structured_answer = StructuredAnswer(**tool_use.input)
            except ValidationError as e:
                raise LLMProviderError(
                    provider="anthropic",
                    error_type="invalid_response",
                    message=f"Failed to parse structured output: {e!s}",
                ) from e

            # Create usage record
            usage = LLMUsage(
                prompt_tokens=response.usage.input_tokens if response.usage else 0,
                completion_tokens=response.usage.output_tokens if response.usage else 0,
                total_tokens=(response.usage.input_tokens + response.usage.output_tokens) if response.usage else 0,
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
                provider="anthropic",
                error_type="generation_failed",
                message=f"Failed to generate structured output: {e!s}",
            ) from e

    def _build_structured_prompt(
        self,
        prompt: str,
        context_documents: list[dict[str, Any]],
        config: StructuredOutputConfig,
        template: PromptTemplateBase | None = None,
    ) -> str:
        """Build a prompt that includes context documents for structured output.

        Args:
            prompt: User's query
            context_documents: Retrieved documents with metadata
            config: Structured output configuration
            template: Optional prompt template for structured output

        Returns:
            Formatted prompt with context
        """

        # Format context documents with configurable truncation
        def truncate_content(content: str, max_length: int) -> str:
            """Truncate content with ellipsis indicator."""
            if len(content) <= max_length:
                return content
            return content[:max_length] + "..."

        # Format context documents with all available metadata
        context_parts = []
        for i, doc in enumerate(context_documents[: config.max_citations]):
            doc_info = [
                f"Document {i + 1} (ID: {doc.get('id', 'unknown')}):",
                f"  Title: {doc.get('title', 'Untitled')}",
            ]

            # Add page_number if available
            if doc.get("page_number") is not None:
                doc_info.append(f"  Page: {doc.get('page_number')}")

            # Add chunk_id if available
            if doc.get("chunk_id") is not None:
                doc_info.append(f"  Chunk ID: {doc.get('chunk_id')}")

            # Add content with truncation
            doc_info.append(f"  Content: {truncate_content(doc.get('content', ''), config.max_context_per_doc)}")

            context_parts.append("\n".join(doc_info))

        context_text = "\n\n".join(context_parts)

        # If template provided, use it
        if template:
            try:
                return template.format_prompt(question=prompt, context=context_text)
            except Exception as e:
                self.logger.warning(f"Template formatting failed: {e}, falling back to default")

        # Default prompt (fallback)
        prompt_parts = [
            f"Question: {prompt}",
            "\nContext Documents:",
            context_text,
            "\nPlease provide a structured answer using the provide_structured_answer tool with:",
            "1. A clear, concise answer to the question",
            "2. A confidence score (0.0-1.0) based on the quality and relevance of the sources",
            "3. Citations to specific documents that support your answer",
            "   - Include the document_id, title, and excerpt from the document",
            "   - If a document has a page_number, include it in your citation",
            "   - If a document has a chunk_id, include it in your citation",
            "   - Extract the most relevant excerpt that supports your answer",
        ]

        if config.include_reasoning:
            prompt_parts.append("4. Step-by-step reasoning showing how you arrived at your answer")

        return "\n".join(prompt_parts)

    def _get_anthropic_tool_schema(self, config: StructuredOutputConfig) -> dict[str, Any]:
        """Get Anthropic-compatible tool schema for structured output.

        Args:
            config: Structured output configuration

        Returns:
            Tool schema dictionary for Anthropic API
        """
        tool = {
            "name": "provide_structured_answer",
            "description": "Provide a structured answer with citations and confidence score",
            "input_schema": {
                "type": "object",
                "properties": {
                    "answer": {"type": "string", "description": "The main answer text"},
                    "confidence": {
                        "type": "number",
                        "description": "Confidence score between 0.0 and 1.0",
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
                                "page_number": {"type": "integer", "description": "Page number (optional)"},
                                "relevance_score": {
                                    "type": "number",
                                    "description": "Relevance score between 0.0 and 1.0",
                                },
                                "chunk_id": {"type": "string", "description": "Chunk identifier (optional)"},
                            },
                            "required": ["document_id", "title", "excerpt", "relevance_score"],
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
            },
        }

        # Add reasoning_steps if requested
        if config.include_reasoning:
            tool["input_schema"]["properties"]["reasoning_steps"] = {
                "type": "array",
                "description": "Step-by-step reasoning process",
                "items": {
                    "type": "object",
                    "properties": {
                        "step_number": {"type": "integer", "description": "Step number"},
                        "thought": {"type": "string", "description": "Reasoning or analysis"},
                        "conclusion": {"type": "string", "description": "Conclusion from this step"},
                        "citations": {
                            "type": "array",
                            "description": "Citations for this step",
                            "items": {"type": "object"},
                        },
                    },
                    "required": ["step_number", "thought", "conclusion"],
                },
            }

        return tool

    def close(self) -> None:
        """Clean up provider resources."""
        if hasattr(self, "client") and self.client:
            self.client.close()
        super().close()
