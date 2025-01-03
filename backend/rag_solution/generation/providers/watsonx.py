"""WatsonX provider implementation using IBM watsonx.ai API."""

from typing import Dict, List, Optional, Union, Generator, Any
import asyncio
from core.logging_utils import get_logger

from ibm_watsonx_ai import APIClient, Credentials
from ibm_watsonx_ai.metanames import EmbedTextParamsMetaNames as EmbedParams
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams
from ibm_watsonx_ai.foundation_models import ModelInference, Embeddings as wx_Embeddings

from .base import LLMProvider, ProviderConfig, PROVIDER_ERROR_TYPES
from vectordbs.data_types import EmbeddingsList
from core.custom_exceptions import LLMProviderError
from rag_solution.schemas.llm_parameters_schema import LLMParametersBase
from rag_solution.schemas.prompt_template_schema import PromptTemplateBase
from rag_solution.services.provider_config_service import ProviderConfigService

logger = get_logger("llm.providers.watsonx")

class WatsonXProvider(LLMProvider):
    """WatsonX provider implementation using IBM watsonx.ai API."""

    def __init__(self, provider_config_service: ProviderConfigService) -> None:
        """Initialize WatsonX provider.
        
        Args:
            provider_config_service: Service for provider configuration
        """
        try:
            # Initialize base attributes
            self.provider_config_service = provider_config_service
            self.client = None
            self.embeddings_client = None
            self._model_cache = {}
            
            # Get and validate configuration
            self._provider_config = self.provider_config_service.get_provider_config("watsonx")
            if not self._provider_config:
                raise LLMProviderError(
                    provider="watsonx",
                    error_type=PROVIDER_ERROR_TYPES["CONFIG_INVALID"],
                    message="No configuration found for WatsonX provider"
                )

            # Validate required fields
            if not self._provider_config.api_url:
                raise LLMProviderError(
                    provider="watsonx",
                    error_type=PROVIDER_ERROR_TYPES["CONFIG_INVALID"],
                    message="api_url is required for WatsonX provider"
                )
            if not self._provider_config.project_id:
                raise LLMProviderError(
                    provider="watsonx",
                    error_type=PROVIDER_ERROR_TYPES["CONFIG_INVALID"],
                    message="project_id is required for WatsonX provider"
                )
            
            # Initialize base class and client
            super().__init__()
            
        except LLMProviderError:
            raise
        except Exception as e:
            raise LLMProviderError(
                provider="watsonx",
                error_type=PROVIDER_ERROR_TYPES["INIT_FAILED"],
                message=f"Failed to initialize provider: {str(e)}"
            )
    
    def initialize_client(self) -> None:
        """Initialize WatsonX client."""
        try:
            # Initialize main client
            self.client = APIClient(
                project_id=self._provider_config.project_id,
                credentials=Credentials(
                    api_key=self._provider_config.api_key,
                    url=self._provider_config.api_url
                )
            )

            # Initialize embeddings client if model specified
            if self._provider_config.embedding_model:
                self.embeddings_client = wx_Embeddings(
                    model_id=self._provider_config.embedding_model,
                    project_id=self._provider_config.project_id,
                    credentials=Credentials(
                        api_key=self._provider_config.api_key,
                        url=self._provider_config.api_url
                    ),
                    params={
                        EmbedParams.RETURN_OPTIONS: {"input_text": True}
                    }
                )

        except Exception as e:
            if "authentication" in str(e).lower():
                raise LLMProviderError(
                    provider="watsonx",
                    error_type=PROVIDER_ERROR_TYPES["AUTH_FAILED"],
                    message=f"Authentication failed: {str(e)}"
                )
            raise LLMProviderError(
                provider="watsonx",
                error_type=PROVIDER_ERROR_TYPES["INIT_FAILED"],
                message=f"Failed to initialize client: {str(e)}"
            )

    def _get_model(self) -> ModelInference:
        """Get cached or create new model instance."""
        try:
            # Use model_id from base class or default from config
            model_id = self._model_id or self._provider_config.default_model_id
            
            # Create new model instance if needed
            if model_id not in self._model_cache:
                model = ModelInference(
                    model_id=model_id,
                    project_id=self._provider_config.project_id,
                    credentials=Credentials(
                        api_key=self._provider_config.api_key,
                        url=self._provider_config.api_url
                    )
                )
                model.set_api_client(api_client=self.client)
                
                # Set parameters if available
                if self._parameters:
                    model.params.update({
                        GenParams.MAX_NEW_TOKENS: self._parameters.get('max_new_tokens', 150),
                        GenParams.TEMPERATURE: self._parameters.get('temperature', 0.7),
                        GenParams.TOP_K: self._parameters.get('top_k', 50),
                        GenParams.TOP_P: self._parameters.get('top_p', 1.0),
                        GenParams.RANDOM_SEED: self._parameters.get('random_seed', None)
                    })
                
                self._model_cache[model_id] = model
                
            return self._model_cache[model_id]
            
        except Exception as e:
            raise LLMProviderError(
                provider="watsonx",
                error_type=PROVIDER_ERROR_TYPES["MODEL_ERROR"],
                message=f"Failed to initialize model: {str(e)}"
            )

    def generate_text(
        self,
        prompt: Union[str, List[str]],
        model_parameters: LLMParametersBase,
        template: Optional[PromptTemplateBase] = None,
        provider_config: Optional[ProviderConfig] = None,
        variables: Optional[Dict[str, Any]] = None
    ) -> Union[str, List[str]]:
        """Generate text using the WatsonX model."""
        try:
            self._ensure_client()
            
            # Prepare prompt using template if provided
            prepared_prompt = self._prepare_prompts(prompt, template, variables)
            
            # Get model (parameters already set in _get_model)
            model = self._get_model()
            
            # Generate text
            response = model.generate_text(prompt=prepared_prompt)

            # Handle batch responses
            if isinstance(prompt, list):
                if isinstance(response, dict) and 'results' in response:
                    return [r['generated_text'].strip() for r in response['results']]
                elif isinstance(response, list):
                    return [r.strip() if isinstance(r, str) else r['generated_text'].strip() for r in response]
                else:
                    raise LLMProviderError(
                        provider="watsonx",
                        error_type=PROVIDER_ERROR_TYPES["RESPONSE_ERROR"],
                        message=f"Unexpected batch response type: {type(response)}"
                    )
            
            # Handle single response
            if isinstance(response, dict):
                if 'results' in response:
                    return response['results'][0]['generated_text'].strip()
                elif 'generated_text' in response:
                    return response['generated_text'].strip()
                
            return response.strip() if isinstance(response, str) else response['generated_text'].strip()
            
        except LLMProviderError:
            raise
        except Exception as e:
            raise LLMProviderError(
                provider="watsonx",
                error_type=PROVIDER_ERROR_TYPES["API_ERROR"],
                message=f"Failed to generate text: {str(e)}"
            )

    def generate_text_stream(
        self,
        prompt: str,
        model_parameters: LLMParametersBase,
        template: Optional[PromptTemplateBase] = None,
        provider_config: Optional[ProviderConfig] = None,
        variables: Optional[Dict[str, Any]] = None
    ) -> Generator[str, None, None]:
        """Generate text in streaming mode."""
        try:
            self._ensure_client()
            
            # Prepare prompt using template if provided
            prepared_prompt = self._prepare_prompts(prompt, template, variables)
            
            # Get model (parameters already set in _get_model)
            model = self._get_model()
            
            # Stream generation
            for chunk in model.generate_text_stream(prompt=prepared_prompt):
                if chunk and chunk.strip():
                    yield chunk.strip()
                    
        except LLMProviderError:
            raise
        except Exception as e:
            raise LLMProviderError(
                provider="watsonx",
                error_type=PROVIDER_ERROR_TYPES["API_ERROR"],
                message=f"Failed to generate streaming text: {str(e)}"
            )

    def get_embeddings(
        self,
        texts: Union[str, List[str]],
        provider_config: Optional[ProviderConfig] = None
    ) -> EmbeddingsList:
        """Generate embeddings for texts."""
        try:
            self._ensure_client()
            
            # Check embeddings support
            if not self.embeddings_client:
                raise LLMProviderError(
                    provider="watsonx",
                    error_type=PROVIDER_ERROR_TYPES["CONFIG_INVALID"],
                    message="Embeddings not configured - no embedding model specified"
                )
            
            # Convert to list
            if isinstance(texts, str):
                texts = [texts]
            
            # Generate embeddings without runtime settings since they're not supported
            embedding_vectors = self.embeddings_client.embed_documents(texts=texts)
            
            return embedding_vectors
            
        except LLMProviderError:
            raise
        except Exception as e:
            raise LLMProviderError(
                provider="watsonx",
                error_type=PROVIDER_ERROR_TYPES["API_ERROR"],
                message=f"Failed to generate embeddings: {str(e)}"
            )

    def close(self) -> None:
        """Clean up provider resources."""
        try:
            for model in self._model_cache.values():
                if hasattr(model, 'close_persistent_connection'):
                    model.close_persistent_connection()
                    
            self._model_cache.clear()
            self.embeddings_client = None
            self.client = None
            
        except Exception as e:
            logger.error(f"Error closing WatsonX provider: {str(e)}")
