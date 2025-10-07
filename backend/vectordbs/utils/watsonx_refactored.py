"""
Refactored WatsonX utilities with proper dependency injection.
This shows how to migrate from module-level settings access to proper patterns.
"""

import logging
from collections.abc import Generator
from typing import Any, ClassVar

import numpy as np
from chromadb.api.types import Documents, EmbeddingFunction
from core.config import Settings, get_settings
from dotenv import load_dotenv
from ibm_watsonx_ai import APIClient, Credentials
from ibm_watsonx_ai.foundation_models import Embeddings as wx_Embeddings
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.metanames import EmbedTextParamsMetaNames as EmbedParams
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

from vectordbs.data_types import EmbeddingsList

# Configure logging
logger = logging.getLogger(__name__)

# Rate limiting settings (these are constants, not from config)
RATE_LIMIT = 10  # maximum number of requests per minute
RATE_LIMIT_PERIOD = 60  # in seconds


class WatsonXClient:
    """
    Singleton-like client manager that handles WatsonX connections.
    Uses dependency injection for settings.
    """

    _instances: ClassVar[dict[str, "WatsonXClient"]] = {}

    def __init__(self, settings: Settings):
        """Initialize with injected settings."""
        self.settings = settings
        self.watsonx_instance_id = settings.wx_project_id
        self.embedding_model = settings.embedding_model
        self._client: APIClient | None = None
        self._embeddings_client: wx_Embeddings | None = None
        self.last_api_call = 0

    @classmethod
    def get_instance(cls, settings: Settings | None = None) -> "WatsonXClient":
        """
        Get or create a WatsonXClient instance.

        Args:
            settings: Settings object. If None, uses get_settings()

        Returns:
            WatsonXClient instance
        """
        if settings is None:
            settings = get_settings()

        # Use project_id as cache key
        cache_key = settings.wx_project_id or "default"

        if cache_key not in cls._instances:
            cls._instances[cache_key] = cls(settings)

        return cls._instances[cache_key]

    def get_client(self) -> APIClient:
        """Get or create the API client."""
        if self._client is None:
            load_dotenv(override=True)
            self._client = APIClient(
                project_id=self.watsonx_instance_id,
                credentials=Credentials(api_key=self.settings.wx_api_key, url=self.settings.wx_url),
            )
        return self._client

    def get_embeddings_client(self, embed_params: dict | None = None) -> wx_Embeddings:
        """Get or create the embeddings client."""
        if self._embeddings_client is None:
            if embed_params is None:
                embed_params = {
                    EmbedParams.TRUNCATE_INPUT_TOKENS: 3,
                    EmbedParams.RETURN_OPTIONS: {"input_text": True},
                }

            api_client = self.get_client()
            self._embeddings_client = wx_Embeddings(
                model_id=self.embedding_model,
                params=embed_params,
                credentials=Credentials(api_key=self.settings.wx_api_key, url=self.settings.wx_url),
                project_id=self.watsonx_instance_id,
            )
            self._embeddings_client.set_api_client(api_client)  # pylint: disable=no-member

        return self._embeddings_client

    def get_model(self, generate_params: dict | None = None, model_id: str | None = None) -> ModelInference:
        """Get a model inference instance."""
        if model_id is None:
            model_id = self.settings.rag_llm

        if generate_params is None:
            generate_params = {
                GenParams.MAX_NEW_TOKENS: self.settings.max_new_tokens,
                GenParams.MIN_NEW_TOKENS: self.settings.min_new_tokens,
                GenParams.TEMPERATURE: self.settings.temperature,
                GenParams.TOP_K: self.settings.top_k,
                GenParams.RANDOM_SEED: self.settings.random_seed,
            }

        api_client = self.get_client()
        model_inference = ModelInference(
            persistent_connection=True,
            model_id=model_id,
            params=generate_params,
            credentials=Credentials(api_key=self.settings.wx_api_key, url=self.settings.wx_url),
            project_id=self.watsonx_instance_id,
        )
        model_inference.set_api_client(api_client=api_client)
        return model_inference


# Standalone utility functions that don't need state
def sublist(inputs: list, n: int) -> Generator[list, None, None]:
    """
    Returns a generator object that yields successive n-sized lists from the main list.

    :param inputs: List: list of chunks
    :param n: int: size of each sublist
    :return: A generator object
    """
    if n <= 0:
        raise ValueError("sublist size n must be a positive integer.")

    for i in range(0, len(inputs), n):
        yield inputs[i : i + n]


# Updated functions with settings parameter
def get_embeddings(
    texts: str | list[str], embed_client: wx_Embeddings | None = None, settings: Settings | None = None
) -> EmbeddingsList:
    """
    Get embeddings for the given texts.

    Args:
        texts: Text or list of texts to embed
        embed_client: Optional pre-configured embeddings client
        settings: Optional settings object. If None, uses get_settings()

    Returns:
        List of embeddings
    """
    if settings is None:
        settings = get_settings()

    if embed_client is None:
        wx_client = WatsonXClient.get_instance(settings)
        embed_client = wx_client.get_embeddings_client()

    if not isinstance(texts, list):
        texts = [texts]

    try:
        logger.info("Generating embeddings for %d text(s)", len(texts))
        embeddings = embed_client.embed_documents(texts=texts)
        return embeddings
    except Exception as e:
        logger.error("Error generating embeddings: %s", e)
        raise


def get_model(
    generate_params: dict | None = None, model_id: str | None = None, settings: Settings | None = None
) -> ModelInference:
    """
    Get a model inference instance.

    Args:
        generate_params: Optional generation parameters
        model_id: Optional model ID (defaults to settings.rag_llm)
        settings: Optional settings object. If None, uses get_settings()

    Returns:
        ModelInference instance
    """
    if settings is None:
        settings = get_settings()

    wx_client = WatsonXClient.get_instance(settings)
    return wx_client.get_model(generate_params, model_id)


def generate_text(
    prompt: str, wx_model: ModelInference | None = None, settings: Settings | None = None, **kwargs
) -> str:
    """
    Generate text using WatsonX.

    Args:
        prompt: The prompt for text generation
        wx_model: Optional pre-configured model
        settings: Optional settings object. If None, uses get_settings()
        **kwargs: Additional parameters for generation

    Returns:
        Generated text
    """
    if settings is None:
        settings = get_settings()

    if wx_model is None:
        wx_model = get_model(settings=settings)

    try:
        response = wx_model.generate_text(prompt=prompt, **kwargs)
        return response
    except Exception as e:
        logger.error("Error generating text: %s", e)
        raise


class ChromaEmbeddingFunction(EmbeddingFunction):
    """
    ChromaDB-compatible embedding function using dependency injection.
    """

    def __init__(self, settings: Settings | None = None):
        """
        Initialize with optional settings.

        Args:
            settings: Optional settings object. If None, uses get_settings()
        """
        if settings is None:
            settings = get_settings()
        self.settings = settings
        self.wx_client = WatsonXClient.get_instance(settings)

    def __call__(self, input_docs: Documents) -> list[Any]:  # pylint: disable=redefined-builtin
        """Embed the input documents."""
        embed_client = self.wx_client.get_embeddings_client()
        embeddings = embed_client.embed_documents(texts=input_docs)
        # Convert to the expected format for ChromaDB

        return [np.array(embedding, dtype=np.float32) for embedding in embeddings]


# Backward compatibility functions
# These maintain the old interface but use dependency injection internally


def _get_client() -> APIClient:
    """
    DEPRECATED: Backward compatibility function.
    Use WatsonXClient.get_instance().get_client() instead.
    """
    settings = get_settings()
    wx_client = WatsonXClient.get_instance(settings)
    return wx_client.get_client()


def _get_embeddings_client(embed_params: dict | None = None) -> wx_Embeddings:
    """
    DEPRECATED: Backward compatibility function.
    Use WatsonXClient.get_instance().get_embeddings_client() instead.
    """
    settings = get_settings()
    wx_client = WatsonXClient.get_instance(settings)
    return wx_client.get_embeddings_client(embed_params)


# For very specific backward compatibility, we can create these at function call time
# instead of module load time
def get_watsonx_instance_id() -> str:
    """Get the WatsonX instance ID from current settings."""
    return get_settings().wx_project_id


def get_embedding_model() -> str:
    """Get the embedding model from current settings."""
    return get_settings().embedding_model


# Example of how to use in FastAPI routes
# Example usage:
# from fastapi import APIRouter, Depends
# from typing import Annotated
# from core.config import Settings, get_settings
# router = APIRouter()
#
# @router.post("/embeddings")
# async def create_embeddings(
#     texts: list[str],
#     settings: Annotated[Settings, Depends(get_settings)]
# ):
#     # Now settings is injected by FastAPI
#     embeddings = get_embeddings(texts, settings=settings)
#     return {"embeddings": embeddings}
#
# @router.post("/generate")
# async def generate(
#     prompt: str,
#     settings: Annotated[Settings, Depends(get_settings)]
# ):
#     # Settings is injected
#     text = generate_text(prompt, settings=settings)
#     return {"generated": text}
