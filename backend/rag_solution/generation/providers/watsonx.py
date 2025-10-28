"""WatsonX provider implementation using IBM watsonx.ai API."""

from __future__ import annotations

import time
from collections.abc import Generator, Sequence
from typing import Any

from ibm_watsonx_ai import APIClient, Credentials
from ibm_watsonx_ai.foundation_models import Embeddings as wx_Embeddings
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.metanames import EmbedTextParamsMetaNames as EmbedParams
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams
from pydantic import UUID4

from core.config import get_settings
from core.custom_exceptions import LLMProviderError, NotFoundError, ValidationError
from core.logging_utils import get_logger
from rag_solution.schemas.llm_model_schema import ModelType
from rag_solution.schemas.llm_parameters_schema import LLMParametersInput
from rag_solution.schemas.prompt_template_schema import PromptTemplateBase
from vectordbs.data_types import EmbeddingsList

from .base import LLMBase

logger = get_logger("llm.providers.watsonx")


class WatsonXLLM(LLMBase):
    """WatsonX provider implementation using IBM watsonx.ai API."""

    def initialize_client(self) -> None:
        """Initialize WatsonX client."""
        try:
            # Get provider configuration as Pydantic model
            self._provider = self._get_provider_config("watsonx")

            logger.debug(
                "Initializing WatsonX client with project_id: %s",
                self._provider.project_id,
            )
            logger.debug("Using base_url: %s", self._provider.base_url)

            try:
                # Convert Pydantic model fields to strings for IBM client
                api_key_value = self._provider.api_key.get_secret_value()
                logger.debug("DEBUG: API key type: %s", type(self._provider.api_key))
                logger.debug("DEBUG: API key value: '%s'", api_key_value)
                logger.debug(
                    "DEBUG: API key length: %s",
                    len(api_key_value) if api_key_value else "None",
                )
                credentials = Credentials(api_key=api_key_value, url=str(self._provider.base_url))
                logger.debug("Created IBM credentials")

                self.client = APIClient(project_id=str(self._provider.project_id), credentials=credentials)
                logger.debug("Created IBM API client")
            except Exception as e:
                logger.error("Error creating IBM client: %s", e)
                raise

            # Get models for this provider
            self._models = self.llm_model_service.get_models_by_provider(self._provider.id)
            self._initialize_embeddings_client()

        except Exception as e:
            raise LLMProviderError(
                provider=self._provider_name,
                error_type="initialization_failed",
                message=f"Failed to initialize client: {e!s}",
            ) from e

    def _initialize_embeddings_client(self) -> None:
        """Initialize the embeddings client if an embedding model is available."""
        logger.debug("Trying to find embedding model")
        logger.debug("Available models: %s", [m.model_id for m in self._models])
        embedding_model = next((m for m in self._models if m.model_type == ModelType.EMBEDDING), None)
        logger.debug("Embedding Model found: %s", embedding_model)
        if embedding_model:
            # Get settings for rate limiting configuration
            settings = get_settings()
            batch_size = getattr(settings, "embedding_batch_size", 10)
            concurrency_limit = getattr(settings, "embedding_concurrency_limit", 1)

            logger.info(
                "Initializing embeddings client with batch_size=%d, concurrency_limit=%d",
                batch_size,
                concurrency_limit,
            )

            self.embeddings_client = wx_Embeddings(
                model_id=str(embedding_model.model_id),
                project_id=str(self._provider.project_id),
                credentials=Credentials(
                    api_key=self._provider.api_key.get_secret_value(),
                    url=str(self._provider.base_url),
                ),
                params={EmbedParams.RETURN_OPTIONS: {"input_text": True}},
            )
            logger.debug("Embeddings client: %s", self.embeddings_client)
        else:
            logger.warning("No embedding model found for provider %s", self._provider_name)
            self.embeddings_client = None

    def _get_model(self, user_id: UUID4, model_parameters: LLMParametersInput | None = None) -> ModelInference:
        """Get a configured model instance with rate limiting."""
        model_id = self._model_id or self._get_default_model_id()

        # Get parameters BEFORE creating model (like direct test script)
        params = self._get_generation_params(user_id, model_parameters)

        # Get settings for rate limiting configuration
        settings = get_settings()
        max_retries = getattr(settings, "llm_max_retries", 10)
        delay_time = getattr(settings, "llm_delay_time", 0.5)

        logger.info(
            "Initializing ModelInference with max_retries=%d, delay_time=%f",
            max_retries,
            delay_time,
        )

        model = ModelInference(
            model_id=str(model_id),
            project_id=str(self._provider.project_id),
            credentials=Credentials(
                api_key=self._provider.api_key.get_secret_value(),
                url=str(self._provider.base_url),
            ),
            params=params,  # Pass params during initialization like direct test
        )
        model.set_api_client(api_client=self.client)

        logger.info("Model ID: %s", model_id)
        logger.info("Model parameters: %s", model.params)
        return model

    def _get_default_model_id(self) -> str:
        """
        Get default model from configuration.

        Simply return the model specified in RAG_LLM from .env.
        This ensures consistency and avoids database lookup issues.

        Returns:
            Model ID string

        Raises:
            ValueError: If RAG_LLM is not configured
        """
        from core.config import get_settings

        settings = get_settings()

        # Validate that RAG_LLM is configured
        if not settings.rag_llm or settings.rag_llm.strip() == "":
            raise ValueError(
                "RAG_LLM environment variable is not configured. "
                "Please set RAG_LLM in your .env file (e.g., RAG_LLM=ibm/granite-3-3-8b-instruct)"
            )

        # Use RAG_LLM from settings as the source of truth
        rag_llm_id = settings.rag_llm
        logger.info(f"Using configured model from RAG_LLM setting: {rag_llm_id}")
        return rag_llm_id

    def _get_generation_params(
        self, user_id: UUID4, model_parameters: LLMParametersInput | None = None
    ) -> dict[str, Any]:
        """Get generation parameters for WatsonX.

        Args:
            user_id: User UUID4
            model_parameters: Optional parameters to use directly

        Returns:
            Dict of WatsonX generation parameters
        """
        # Use provided parameters if available
        params = model_parameters or self.llm_parameters_service.get_latest_or_default_parameters(user_id)

        if params is None:
            raise ValueError("No LLM parameters found for user")

        # Convert to WatsonX format
        return {
            GenParams.DECODING_METHOD: "sample",
            GenParams.MAX_NEW_TOKENS: params.max_new_tokens,
            GenParams.TEMPERATURE: params.temperature,
            GenParams.TOP_K: params.top_k,
            GenParams.TOP_P: params.top_p,
        }

    def generate_text(
        self,
        user_id: UUID4,
        prompt: str | Sequence[str],
        model_parameters: LLMParametersInput | None = None,
        template: PromptTemplateBase | None = None,
        variables: dict[str, Any] | None = None,
    ) -> str | list[str]:
        """Generate text using WatsonX model."""
        try:
            logger.debug("Generating text for user %s with %d prompt(s)", user_id, len(prompt))
            self._ensure_client()
            model = self._get_model(user_id, model_parameters)

            # Handle batch generation with concurrency_limit
            if isinstance(prompt, list):
                # Check if prompts are already formatted strings or need template formatting
                if template is None:
                    # Prompts are already formatted - use them directly
                    formatted_prompts = prompt
                    logger.debug("Using pre-formatted prompts for batch generation")
                else:
                    # Prompts need template formatting
                    formatted_prompts = []
                    for text in prompt:
                        # For each text, create a new variables dict with the text as context
                        prompt_variables = {"context": text}
                        if variables:
                            prompt_variables.update(variables)

                        formatted = self.prompt_template_service.format_prompt_with_template(template, prompt_variables)
                        formatted_prompts.append(formatted)
                        logger.debug("Formatted prompt: %s...", formatted[:200])  # Log first 200 chars

                response = model.generate_text(
                    prompt=formatted_prompts,
                    concurrency_limit=8,  # Max concurrency limit
                )

                logger.debug("Response from IBM watsonx: %s", response)
                if isinstance(response, dict) and "results" in response:
                    return [r["generated_text"].strip() for r in response["results"]]
                elif isinstance(response, list):
                    return [r["generated_text"].strip() if isinstance(r, dict) else r.strip() for r in response]
                else:
                    return [str(response).strip()]
            else:
                # Single prompt handling
                logger.info(
                    "=== ENTERING SINGLE PROMPT PATH === prompt=%s, template=%s",
                    prompt[:50] if prompt else "EMPTY",
                    template is not None,
                )

                if template is None:
                    raise ValueError("Template is required for text generation")

                prompt_variables = {"context": prompt}
                if variables:
                    prompt_variables.update(variables)

                formatted_prompt = self.prompt_template_service.format_prompt_with_template(template, prompt_variables)
                logger.info("=== FORMATTED PROMPT LENGTH: %d chars ===", len(formatted_prompt))
                logger.debug("Formatted single prompt: %s...", formatted_prompt[:200])

                # Save full prompt to file for debugging (especially useful for podcast generation)
                import os
                from datetime import datetime

                debug_dir = "/tmp/watsonx_prompts"
                os.makedirs(debug_dir, exist_ok=True)

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                prompt_file = f"{debug_dir}/prompt_{timestamp}_{user_id}.txt"

                try:
                    with open(prompt_file, "w", encoding="utf-8") as f:
                        f.write("=" * 80 + "\n")
                        f.write(f"WatsonX Prompt Debug - {datetime.now().isoformat()}\n")
                        f.write("=" * 80 + "\n")
                        f.write(f"User ID: {user_id}\n")
                        f.write(f"Model: {model.model_id}\n")
                        f.write(f"Parameters: {model.params}\n")
                        f.write("=" * 80 + "\n\n")
                        f.write("FULL FORMATTED PROMPT:\n")
                        f.write("-" * 80 + "\n")
                        f.write(formatted_prompt)
                        f.write("\n" + "-" * 80 + "\n")
                    logger.info("Saved full prompt to: %s", prompt_file)
                except Exception as e:
                    logger.warning("Failed to save prompt to file: %s", e)

                response = model.generate_text(prompt=formatted_prompt)
                logger.debug("Response from model: %s", response)

                result: str
                if isinstance(response, dict) and "results" in response:
                    result = response["results"][0]["generated_text"].strip()
                elif isinstance(response, list):
                    first_result = response[0]
                    result = (
                        first_result["generated_text"].strip()
                        if isinstance(first_result, dict)
                        else first_result.strip()
                    )
                else:
                    result = str(response).strip()

                # Save response to same file for comparison
                try:
                    with open(prompt_file, "a", encoding="utf-8") as f:
                        f.write("\n\n")
                        f.write("=" * 80 + "\n")
                        f.write("RAW LLM RESPONSE:\n")
                        f.write("-" * 80 + "\n")
                        f.write(result)
                        f.write("\n" + "-" * 80 + "\n")
                        f.write(f"\nResponse length: {len(result)} characters\n")
                        f.write(f"Response word count: {len(result.split())} words\n")
                    logger.info("Appended response to: %s", prompt_file)
                except Exception as e:
                    logger.warning("Failed to append response to file: %s", e)

                return result

        except (ValidationError, NotFoundError) as e:
            raise LLMProviderError(
                provider=self._provider_name,
                error_type="invalid_template" if isinstance(e, ValidationError) else "template_not_found",
                message=str(e),
            ) from e
        except Exception as e:
            logger.error("Error in generate_text: %s", e)
            logger.exception(e)
            raise LLMProviderError(
                provider=self._provider_name,
                error_type="generation_failed",
                message=f"Failed to generate text: {e!s}",
            ) from e

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
            model = self._get_model(user_id, model_parameters)

            formatted_prompt = super()._format_prompt(prompt, template, variables)
            for chunk in model.generate_text_stream(prompt=formatted_prompt):
                if chunk and chunk.strip():
                    yield chunk.strip()

        except (ValidationError, NotFoundError) as e:
            raise LLMProviderError(
                provider=self._provider_name,
                error_type="invalid_template" if isinstance(e, ValidationError) else "template_not_found",
                message=str(e),
            ) from e
        except Exception as e:
            raise LLMProviderError(
                provider=self._provider_name,
                error_type="streaming_failed",
                message=f"Failed to generate streaming text: {e!s}",
            ) from e

    def get_embeddings(self, texts: str | Sequence[str]) -> EmbeddingsList:
        """Generate embeddings for texts with robust retry mechanism."""
        try:
            self._ensure_client()

            # Check if embeddings client is initialized
            if self.embeddings_client is None:
                logger.error("Embeddings client is not initialized")
                raise LLMProviderError(
                    provider=self._provider_name,
                    error_type="embeddings_failed",
                    message="Embeddings client is not initialized",
                )

            if isinstance(texts, str):
                texts = [texts]

            logger.debug("Generating embeddings for %d texts", len(texts))
            logger.debug("Embeddings client: %s", self.embeddings_client)

            # Add a configurable delay to prevent rate limiting
            settings = get_settings()
            request_delay = getattr(settings, "embedding_request_delay", 0.2)
            max_retries = getattr(settings, "embedding_max_retries", 10)
            delay_time = getattr(settings, "embedding_delay_time", 0.5)

            time.sleep(request_delay)

            # Implement our own retry mechanism with exponential backoff
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    logger.debug(
                        "Attempt %d: Calling embed_documents with %d texts",
                        attempt + 1,
                        len(texts),
                    )
                    # Use the SDK's built-in rate limiting and batching
                    embeddings = self.embeddings_client.embed_documents(texts=texts)

                    logger.debug("Received embeddings: %s", type(embeddings))
                    logger.debug("Embeddings length: %d", len(embeddings) if embeddings else 0)

                    # Validate embeddings
                    if embeddings is None:
                        logger.error("WatsonX returned None embeddings!")
                        raise ValueError("WatsonX returned None embeddings")

                    if not embeddings:
                        logger.error("WatsonX returned empty embeddings list!")
                        raise ValueError("WatsonX returned empty embeddings list")

                    # Check each embedding individually
                    if isinstance(embeddings, list):
                        for i, emb in enumerate(embeddings):
                            if emb is None:
                                logger.error("Embedding at index %d is None!", i)
                                raise ValueError(f"Embedding at index {i} is None")
                            if not isinstance(emb, list) or not emb:
                                logger.error(
                                    "Embedding at index %d is not a valid list: %s",
                                    i,
                                    type(emb),
                                )
                                raise ValueError(f"Embedding at index {i} is not a valid list")
                            if not all(isinstance(x, int | float) for x in emb):
                                logger.error(
                                    "Embedding at index %d contains non-numeric values",
                                    i,
                                )
                                raise ValueError(f"Embedding at index {i} contains non-numeric values")

                        logger.debug("All %d embeddings validated successfully", len(embeddings))
                        return embeddings
                    else:
                        logger.debug("Converting single embedding to list")
                        if not isinstance(embeddings, list) or not embeddings:
                            logger.error(
                                "Single embedding is not a valid list: %s",
                                type(embeddings),
                            )
                            raise ValueError("Single embedding is not a valid list")
                        return [embeddings]

                except Exception as e:
                    last_exception = e

                    # Check if it's a rate limit error
                    if "429" in str(e) or "rate_limit_reached_requests" in str(e):
                        if attempt < max_retries:
                            # Exponential backoff: delay_time * (2^attempt)
                            backoff_delay = delay_time * (2**attempt)
                            logger.warning(
                                "Rate limit hit (attempt %d/%d), retrying in %.2fs",
                                attempt + 1,
                                max_retries + 1,
                                backoff_delay,
                            )
                            time.sleep(backoff_delay)
                            continue
                        else:
                            logger.error("Rate limit exceeded after %d retries", max_retries)
                            break
                    else:
                        # Non-rate-limit error, don't retry
                        logger.error("Non-retryable error: %s", e)
                        break

            # If we get here, all retries failed
            logger.error(
                "get_embeddings failed after %d retries: %s",
                max_retries,
                last_exception,
            )
            raise LLMProviderError(
                provider=self._provider_name,
                error_type="embeddings_failed",
                message=f"Failed to generate embeddings after {max_retries} retries: {last_exception!s}",
            ) from last_exception

        except LLMProviderError:
            raise
        except Exception as e:
            logger.error("get_embeddings failed: %s", e)
            raise LLMProviderError(
                provider=self._provider_name,
                error_type="embeddings_failed",
                message=f"Failed to generate embeddings: {e!s}",
            ) from e

    def close(self) -> None:
        """Clean up provider resources."""
        if hasattr(self, "embeddings_client"):
            self.embeddings_client = None
        super().close()
