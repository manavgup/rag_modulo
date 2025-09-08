"""WatsonX provider implementation using IBM watsonx.ai API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ibm_watsonx_ai import APIClient, Credentials  # type: ignore[import-untyped]
from ibm_watsonx_ai.foundation_models import Embeddings as wx_Embeddings  # type: ignore[import-untyped]
from ibm_watsonx_ai.foundation_models import ModelInference  # type: ignore[import-untyped]
from ibm_watsonx_ai.metanames import EmbedTextParamsMetaNames as EmbedParams  # type: ignore[import-untyped]
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams  # type: ignore[import-untyped]

from core.custom_exceptions import LLMProviderError, NotFoundError, ValidationError
from core.logging_utils import get_logger
from rag_solution.schemas.llm_model_schema import ModelType

from .base import LLMBase

if TYPE_CHECKING:
    from collections.abc import Generator, Sequence

    from pydantic import UUID4

    from rag_solution.schemas.llm_parameters_schema import LLMParametersInput
    from rag_solution.schemas.prompt_template_schema import PromptTemplateBase
    from vectordbs.data_types import EmbeddingsList

logger = get_logger("llm.providers.watsonx")


class WatsonXLLM(LLMBase):
    """WatsonX provider implementation using IBM watsonx.ai API."""

    def initialize_client(self) -> None:
        """Initialize WatsonX client."""
        try:
            # Get provider configuration as Pydantic model
            self._provider = self._get_provider_config("watsonx")

            logger.debug(f"Initializing WatsonX client with project_id: {self._provider.project_id}")
            logger.debug(f"Using base_url: {self._provider.base_url}")

            try:
                # Convert Pydantic model fields to strings for IBM client
                credentials = Credentials(api_key=self._provider.api_key.get_secret_value(), url=str(self._provider.base_url))
                logger.debug("Created IBM credentials")

                self.client = APIClient(project_id=str(self._provider.project_id), credentials=credentials)
                logger.debug("Created IBM API client")
            except Exception as e:
                logger.error(f"Error creating IBM client: {e!s}")
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
        embedding_model = next((m for m in self._models if m.model_type == ModelType.EMBEDDING), None)
        logger.debug(f"Embedding Model found: {embedding_model}")
        if embedding_model:
            self.embeddings_client = wx_Embeddings(
                model_id=str(embedding_model.model_id),
                project_id=str(self._provider.project_id),
                credentials=Credentials(api_key=self._provider.api_key.get_secret_value(), url=str(self._provider.base_url)),
                params={EmbedParams.RETURN_OPTIONS: {"input_text": True}},
            )
            logger.debug(f"Embeddings client: {self.embeddings_client}")

    def _get_model(self, user_id: UUID4, model_parameters: LLMParametersInput | None = None) -> ModelInference:
        """Get a configured model instance."""
        model_id = self._model_id or self._get_default_model_id()
        model = ModelInference(
            model_id=str(model_id),
            project_id=str(self._provider.project_id),
            credentials=Credentials(api_key=self._provider.api_key.get_secret_value(), url=str(self._provider.base_url)),
        )
        model.set_api_client(api_client=self.client)

        # Initialize params dictionary
        model.params = {}

        # Get and update parameters
        params = self._get_generation_params(user_id, model_parameters)
        model.params.update(params)
        logger.info(f"Model ID: {model_id}")
        logger.info(f"Model parameters: {model.params}")
        return model

    def _get_default_model_id(self) -> str:
        """Get the default model ID for text generation."""
        default_model = next((m for m in self._models if m.is_default and m.model_type == ModelType.GENERATION), None)
        if not default_model:
            raise LLMProviderError(provider=self._provider_name, error_type="no_default_model", message="No default model configured")
        return default_model.model_id

    def _get_generation_params(self, user_id: UUID4, model_parameters: LLMParametersInput | None = None) -> dict[str, Any]:
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
            logger.info(f"user_id: {user_id}, prompt: {prompt}, model_parameters: {model_parameters}, template: {template}, variables: {variables}")
            self._ensure_client()
            model = self._get_model(user_id, model_parameters)

            # Handle batch generation with concurrency_limit
            if isinstance(prompt, list):
                formatted_prompts = []
                for text in prompt:
                    # For each text, create a new variables dict with the text as context
                    prompt_variables = {"context": text}
                    if variables:
                        prompt_variables.update(variables)

                    if template is None:
                        raise ValueError("Template is required for batch generation")
                    formatted = self.prompt_template_service.format_prompt_with_template(template, prompt_variables)
                    formatted_prompts.append(formatted)
                    logger.debug(f"Formatted prompt*******: {formatted}")  # Log first 200 chars

                response = model.generate_text(
                    prompt=formatted_prompts,
                    concurrency_limit=10,  # Max concurrency limit
                )

                logger.debug(f"Response: {response}")
                if isinstance(response, dict) and "results" in response:
                    return [r["generated_text"].strip() for r in response["results"]]
                elif isinstance(response, list):
                    return [r["generated_text"].strip() if isinstance(r, dict) else r.strip() for r in response]
                else:
                    return [str(response).strip()]
            else:
                # Single prompt handling
                if template is None:
                    raise ValueError("Template is required for text generation")

                prompt_variables = {"context": prompt}
                if variables:
                    prompt_variables.update(variables)

                formatted_prompt = self.prompt_template_service.format_prompt_with_template(template, prompt_variables)
                logger.debug(f"Formatted single prompt: {formatted_prompt}...")

                response = model.generate_text(prompt=formatted_prompt)
                logger.debug(f"Response from model: {response}")

                result: str
                if isinstance(response, dict) and "results" in response:
                    result = response["results"][0]["generated_text"].strip()
                elif isinstance(response, list):
                    first_result = response[0]
                    result = first_result["generated_text"].strip() if isinstance(first_result, dict) else first_result.strip()
                else:
                    result = str(response).strip()
                return result

        except (ValidationError, NotFoundError) as e:
            raise LLMProviderError(
                provider=self._provider_name,
                error_type="invalid_template" if isinstance(e, ValidationError) else "template_not_found",
                message=str(e),
            ) from e
        except Exception as e:
            logger.error(f"Error in generate_text: {e!s}")
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
        """Generate embeddings for texts."""
        try:
            self._ensure_client()

            if isinstance(texts, str):
                texts = [texts]

            embeddings = self.embeddings_client.embed_documents(texts=texts)
            # Ensure we return the correct type
            if isinstance(embeddings, list):
                return embeddings
            else:
                # If it's not a list, convert it to the expected format
                return [embeddings] if embeddings else []

        except LLMProviderError:
            raise
        except Exception as e:
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
