"""WatsonX provider implementation using IBM watsonx.ai API."""

from typing import Dict, List, Optional, Union, Generator, Any, Sequence
from uuid import UUID
from core.logging_utils import get_logger
from ibm_watsonx_ai import APIClient, Credentials
from ibm_watsonx_ai.metanames import EmbedTextParamsMetaNames as EmbedParams
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams
from ibm_watsonx_ai.foundation_models import ModelInference, Embeddings as wx_Embeddings

from .base import LLMBase
from vectordbs.data_types import EmbeddingsList
from core.custom_exceptions import LLMProviderError, ValidationError, NotFoundError
from rag_solution.schemas.prompt_template_schema import PromptTemplateBase
from rag_solution.schemas.llm_parameters_schema import LLMParametersInput
from rag_solution.schemas.llm_provider_schema import ModelType
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
                credentials = Credentials(
                    api_key=str(self._provider.api_key),
                    url=str(self._provider.base_url)
                )
                logger.debug("Created IBM credentials")
                
                self.client = APIClient(
                    project_id=str(self._provider.project_id),
                    credentials=credentials
                )
                logger.debug("Created IBM API client")
            except Exception as e:
                logger.error(f"Error creating IBM client: {str(e)}")
                raise

            # Get models for this provider
            self._models = self.llm_provider_service.get_models_by_provider(self._provider.id)
            self._initialize_embeddings_client()

        except Exception as e:
            raise LLMProviderError(
                provider=self._provider_name,
                error_type="initialization_failed",
                message=f"Failed to initialize client: {str(e)}"
            )

    def _initialize_embeddings_client(self) -> None:
        """Initialize the embeddings client if an embedding model is available."""
        logger.debug("Trying to find embedding model")
        embedding_model = next(
            (m for m in self._models if m.model_type == ModelType.EMBEDDING),
            None
        )
        logger.debug(f"Embedding Model found: {embedding_model}")
        if embedding_model:
            self.embeddings_client = wx_Embeddings(
                model_id=str(embedding_model.model_id),
                project_id=str(self._provider.project_id),
                credentials=Credentials(
                    api_key=str(self._provider.api_key),
                    url=str(self._provider.base_url)
                ),
                params={EmbedParams.RETURN_OPTIONS: {"input_text": True}}
            )
            logger.debug(f"Embeddings client: {self.embeddings_client}")

    def _get_model(self, user_id: UUID, model_parameters: Optional[LLMParametersInput] = None) -> ModelInference:
        """Get a configured model instance."""
        model_id = self._model_id or self._get_default_model_id()
        model = ModelInference(
            model_id=str(model_id),
            project_id=str(self._provider.project_id),
            credentials=Credentials(
                api_key=str(self._provider.api_key),
                url=str(self._provider.base_url)
            )
        )
        model.set_api_client(api_client=self.client)

        # Initialize params dictionary
        model.params = {}
        
        # Get and update parameters
        params = self._get_generation_params(user_id, model_parameters)
        model.params.update(params)
        
        logger.debug(f"Model parameters: {model.params}")
        return model

    def _get_default_model_id(self) -> str:
        """Get the default model ID for text generation."""
        default_model = next(
            (m for m in self._models if m.is_default and m.model_type == ModelType.GENERATION),
            None
        )
        if not default_model:
            raise LLMProviderError(
                provider=self._provider_name,
                error_type="no_default_model",
                message="No default model configured"
            )
        return default_model.model_id

    def _get_generation_params(self, user_id: UUID, model_parameters: Optional[LLMParametersInput] = None) -> Dict[str, Any]:
        """Get validated generation parameters."""
        # Get parameters from service and convert to Pydantic model
        params = self.llm_parameters_service.get_parameters(user_id) if not model_parameters else \
            self.llm_parameters_service.create_or_update_parameters(user_id, model_parameters)

        # Use default values if no parameters are found
        if not params:
            return {
                GenParams.MAX_NEW_TOKENS: 150,
                GenParams.TEMPERATURE: 0.7,
                GenParams.TOP_K: 50,
                GenParams.TOP_P: 1.0
            }

        # Parameters are already in Pydantic model form from the service
        return {
            GenParams.MAX_NEW_TOKENS: params.max_new_tokens,
            GenParams.TEMPERATURE: params.temperature,
            GenParams.TOP_K: params.top_k,
            GenParams.TOP_P: params.top_p
        }

    def generate_text(
        self,
        user_id: UUID,
        prompt: Union[str, Sequence[str]],
        model_parameters: Optional[LLMParametersInput] = None,
        template: Optional[PromptTemplateBase] = None,
        variables: Optional[Dict[str, Any]] = None
    ) -> Union[str, list[str]]:
        """Generate text using WatsonX model."""
        try:
            self._ensure_client()
            model = self._get_model(user_id, model_parameters)

            # Handle batch generation with concurrency_limit
            if isinstance(prompt, list):
                formatted_prompts = [
                    self._format_prompt(p, template, variables) for p in prompt
                ]
                response = model.generate_text(
                    prompt=formatted_prompts,
                    concurrency_limit=10  # Max concurrency limit
                )
                if isinstance(response, dict) and 'results' in response:
                    return [r['generated_text'].strip() for r in response['results']]
                elif isinstance(response, list):
                    return [r['generated_text'].strip() if isinstance(r, dict) else r.strip() for r in response]
                else:
                    return [str(response).strip()]
            else:
                formatted_prompt = self._format_prompt(prompt, template, variables)
                response = model.generate_text(prompt=formatted_prompt)
                logger.debug(f"Response from model: {response}")
                
                if isinstance(response, dict) and 'results' in response:
                    return response['results'][0]['generated_text'].strip()
                elif isinstance(response, list):
                    first_result = response[0]
                    return first_result['generated_text'].strip() if isinstance(first_result, dict) else first_result.strip()
                else:
                    return str(response).strip()

        except (ValidationError, NotFoundError) as e:
            raise LLMProviderError(
                provider=self._provider_name,
                error_type="invalid_template" if isinstance(e, ValidationError) else "template_not_found",
                message=str(e)
            )
        except Exception as e:
            raise LLMProviderError(
                provider=self._provider_name,
                error_type="generation_failed",
                message=f"Failed to generate text: {str(e)}"
            )

    def _format_prompt(
        self,
        prompt: str,
        template: Optional[PromptTemplateBase] = None,
        variables: Optional[Dict[str, Any]] = None
    ) -> str:
        """Format a prompt using a template and variables."""
        if template:
            vars_dict = dict(variables or {})
            vars_dict['prompt'] = prompt
            return self.prompt_template_service.format_prompt(template.id, vars_dict)
        return prompt

    def generate_text_stream(
        self,
        user_id: UUID,
        prompt: str,
        model_parameters: Optional[LLMParametersInput] = None,
        template: Optional[PromptTemplateBase] = None,
        variables: Optional[Dict[str, Any]] = None
    ) -> Generator[str, None, None]:
        """Generate text in streaming mode."""
        try:
            self._ensure_client()
            model = self._get_model(user_id, model_parameters)

            formatted_prompt = self._format_prompt(prompt, template, variables)
            for chunk in model.generate_text_stream(prompt=formatted_prompt):
                if chunk and chunk.strip():
                    yield chunk.strip()

        except (ValidationError, NotFoundError) as e:
            raise LLMProviderError(
                provider=self._provider_name,
                error_type="invalid_template" if isinstance(e, ValidationError) else "template_not_found",
                message=str(e)
            )
        except Exception as e:
            raise LLMProviderError(
                provider=self._provider_name,
                error_type="streaming_failed",
                message=f"Failed to generate streaming text: {str(e)}"
            )

    def get_embeddings(
        self,
        texts: Union[str, List[str]]
    ) -> EmbeddingsList:
        """Generate embeddings for texts."""
        try:
            self._ensure_client()

            if isinstance(texts, str):
                texts = [texts]

            return self.embeddings_client.embed_documents(texts=texts)

        except LLMProviderError:
            raise
        except Exception as e:
            raise LLMProviderError(
                provider=self._provider_name,
                error_type="embeddings_failed",
                message=f"Failed to generate embeddings: {str(e)}"
            )

    def close(self) -> None:
        """Clean up provider resources."""
        if hasattr(self, 'embeddings_client'):
            self.embeddings_client = None
        super().close()