#backend/rag_solution/generation/providers/watsonx.py
from typing import Dict, List, Optional, Union, Generator, Any
import asyncio
from core.logging_utils import get_logger
from functools import lru_cache

from dotenv import load_dotenv
from ibm_watsonx_ai import APIClient, Credentials
from ibm_watsonx_ai.metanames import EmbedTextParamsMetaNames as EmbedParams
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams
from ibm_watsonx_ai.foundation_models import ModelInference, Embeddings as wx_Embeddings

from .base import LLMProvider, ProviderConfig
from core.config import settings
from vectordbs.data_types import  EmbeddingsList
from core.custom_exceptions import LLMProviderError
from rag_solution.schemas.model_parameters_schema import ModelParametersInput
from rag_solution.schemas.prompt_template_schema import BasePromptTemplate

logger = get_logger("llm.providers.watsonx")

load_dotenv(override=True)

class WatsonXProvider(LLMProvider):
    """WatsonX provider implementation using IBM watsonx.ai API."""

    def __init__(self) -> None:
        """Initialize WatsonX provider with API client and models."""
        super().__init__()
        self.embedding_model: str = settings.embedding_model
    
    def initialize_client(self) -> None:
        """Initialize WatsonX client and related resources."""
        try:
            self.client = APIClient(
                project_id=settings.wx_project_id,
                credentials=Credentials(
                    api_key=settings.wx_api_key,
                    url=settings.wx_url
                )
            )
            self._model_cache = {}
            
            # Initialize embeddings client
            self._get_embeddings_client()
        except Exception as e:
            logger.error(f"Failed to initialize WatsonX client: {str(e)}")
            raise LLMProviderError(f"Initialization failed: {str(e)}")

    def _get_embeddings_client(self) -> wx_Embeddings:
        """Get or create embeddings client instance."""
        try:
            if not hasattr(self, 'embeddings_client') or self.embeddings_client is None:
                embed_params = {
                    EmbedParams.RETURN_OPTIONS: {"input_text": True},
                }
                self.embeddings_client = wx_Embeddings(
                    persistent_connection=True,
                    model_id=settings.embedding_model,
                    params=embed_params,
                    project_id=settings.wx_project_id,
                    credentials=Credentials(
                        api_key=settings.wx_api_key,
                        url=settings.wx_url
                    )
                )
            return self.embeddings_client
        except Exception as e:
            raise LLMProviderError(f"Failed to get embeddings client: {str(e)}")

    def _get_model(self, model_id: str = settings.rag_llm) -> ModelInference:
        """Get cached or create new model instance."""
        try:
            if model_id not in self._model_cache:
                generate_params = {
                    GenParams.MAX_NEW_TOKENS: settings.max_new_tokens,
                    GenParams.MIN_NEW_TOKENS: settings.min_new_tokens,
                    GenParams.TEMPERATURE: settings.temperature,
                    GenParams.TOP_K: settings.top_k,
                    GenParams.RANDOM_SEED: settings.random_seed,
                }
                
                model = ModelInference(
                    persistent_connection=True,
                    model_id=model_id,
                    params=generate_params,
                    project_id=settings.wx_project_id,
                    credentials=Credentials(
                        api_key=settings.wx_api_key,
                        url=settings.wx_url
                    )
                )
                model.set_api_client(api_client=self.client)
                self._model_cache[model_id] = model
                
            return self._model_cache[model_id]
        except Exception as e:
            raise LLMProviderError(f"Failed to initialize model: {str(e)}")

    def generate_text(
    self,
    prompt: Union[str, List[str]],
    model_parameters: ModelParametersInput,
    template: Optional[BasePromptTemplate] = None,
    provider_config: Optional[ProviderConfig] = None
) -> Union[str, List[str]]:
        """Generate text using the WatsonX model."""
        try:
            self._ensure_client()
            logger.info(f"Generating text with prompt: {prompt[:100]}...")

            # Use default config if none provided
            if provider_config is None:
                provider_config = ProviderConfig()
            
            # Prepare the prompt using the template if provided
            prompt = self._prepare_prompts(prompt, template)
            
            # Get or create model instance
            model = self._get_model()
            
            # Update generation parameters
            model.params.update({
                GenParams.MAX_NEW_TOKENS: model_parameters.max_new_tokens,
                GenParams.TEMPERATURE: model_parameters.temperature,
                GenParams.TOP_K: model_parameters.top_k,
                GenParams.TOP_P: model_parameters.top_p,
                GenParams.RANDOM_SEED: model_parameters.random_seed
            })
            
            response = model.generate_text(prompt=prompt, concurrency_limit=provider_config.concurrency_limit)

             # Log the response type and content
            logger.info(f"Response type: {type(response)}")
            logger.info(f"Response content: {response}")

            # Handle batch responses
            if isinstance(prompt, list):
                if isinstance(response, dict) and 'results' in response:
                    return [r['generated_text'].strip() for r in response['results']]
                elif isinstance(response, list):
                    return [r.strip() if isinstance(r, str) else r['generated_text'].strip() for r in response]
                else:
                    logger.error(f"Unexpected response type: {type(response)}")
                    raise ValueError(f"Unexpected response type: {type(response)}")
            
            # Handle single response
            if isinstance(response, dict):
                if 'results' in response:
                    return response['results'][0]['generated_text'].strip()
                elif 'generated_text' in response:
                    return response['generated_text'].strip()
                
            return response.strip() if isinstance(response, str) else response['generated_text'].strip()
            
        except Exception as e:
            logger.error(f"Text generation failed: {str(e)}")
            raise LLMProviderError(f"Failed to generate text: {str(e)}")

    def generate_text_stream(
        self,
        prompt: str,
        model_parameters: ModelParametersInput,
        template: Optional[BasePromptTemplate] = None,
        provider_config: Optional[ProviderConfig] = None
    ) -> Generator[str, None, None]:
        """Generate text in streaming mode.

        Args:
            prompt (str): Input text prompt.
            model_parameters (ModelParametersInput): Generation parameters from model config.
            template (Optional[PromptTemplateInput]): Optional prompt template.
            provider_config (Optional[ProviderConfig]): Optional provider-specific settings.

        Yields:
            Generator[str, None, None]: Generated text chunks.
        """
        try:
            self._ensure_client()
            logger.info(f"Streaming generation for prompt: {prompt[:100]}...")
            
            # Prepare the prompt using the template if provided
            prompt = self._prepare_prompts(prompt, template)
            
            # Get or create model instance
            model = self._get_model()
            
            # Update generation parameters
            model.params.update({
                GenParams.MAX_NEW_TOKENS: model_parameters.max_new_tokens,
                GenParams.TEMPERATURE: model_parameters.temperature,
                GenParams.RANDOM_SEED: model_parameters.random_seed
            })
            
            # Use stream generation
            stream = model.generate_text_stream(prompt=prompt)
            for chunk in stream:
                if chunk and chunk.strip():
                    yield chunk.strip()
                    
        except Exception as e:
            logger.error(f"Streaming generation failed: {str(e)}")
            raise LLMProviderError(f"Failed to generate streaming text: {str(e)}")

    async def get_embeddings(
        self,
        texts: Union[str, List[str]],
        provider_config: Optional[ProviderConfig] = None
    ) -> EmbeddingsList:
        """Generate embeddings for provided texts.

        Args:
            texts (Union[str, List[str]]): Text or list of texts to embed.
            provider_config (Optional[ProviderConfig]): Optional provider-specific settings.

        Returns:
            EmbeddingsList: List of embedding vectors.
        """
        try:
            self._ensure_client()
            if isinstance(texts, str):
                texts = [texts]
            
            # Use provided client or get default
            embeddings_client = self.embeddings_client or self._get_embeddings_client()
            
            # Generate embeddings using ThreadPoolExecutor
            embedding_vectors = await asyncio.to_thread(
                embeddings_client.embed_documents,
                texts=texts
            )
            
            return embedding_vectors
        except Exception as e:
            logger.error(f"Embedding generation failed: {str(e)}")
            raise LLMProviderError(f"Failed to generate embeddings: {str(e)}")

    def close(self) -> None:
        """Clean up provider resources."""
        try:
            for model in self._model_cache.values():
                if hasattr(model, 'close_persistent_connection'):
                    model.close_persistent_connection()
                    
            self._model_cache.clear()
            self.embeddings_client = None
            self.client = None
            
            logger.info("Successfully closed WatsonX provider connections")
        except Exception as e:
            logger.error(f"Error closing WatsonX provider: {str(e)}")