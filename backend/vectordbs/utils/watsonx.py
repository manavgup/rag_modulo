import asyncio
import json
import logging
import os
from collections.abc import Generator
from functools import lru_cache
from typing import Any

from chromadb.api.types import Documents, EmbeddingFunction
from dotenv import load_dotenv
from ibm_watsonx_ai import APIClient, Credentials
from ibm_watsonx_ai.foundation_models import Embeddings as wx_Embeddings
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.metanames import EmbedTextParamsMetaNames as EmbedParams
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from core.config import Settings, get_settings
from vectordbs.data_types import EmbeddingsList

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Remove global clients - use dependency injection instead


# Rate limiting settings
RATE_LIMIT = 10  # maximum number of requests per minute
RATE_LIMIT_PERIOD = 60  # in seconds

# Timestamp of the last API call
last_api_call = 0


def sublist(inputs: list, n: int) -> Generator[list, None, None]:
    """
    returns a generator object that yields successive n-sized lists from the main list.

    :param inputs: List: list of chunks
    :param n: int: size of each sublist
    :return: A generator object
    """
    if n <= 0:
        raise ValueError("sublist size n must be a positive integer.")

    for i in range(0, len(inputs), n):
        yield inputs[i : i + n]


def get_wx_client(settings: Settings) -> APIClient:
    """Create a WatsonX API client with dependency injection.

    Args:
        settings: Settings object containing WatsonX configuration

    Returns:
        APIClient: Configured WatsonX API client
    """
    load_dotenv(override=True)
    return APIClient(
        project_id=settings.wx_project_id,
        credentials=Credentials(api_key=settings.wx_api_key, url=settings.wx_url),
    )


def get_model(
    settings: Settings = get_settings(), generate_params: dict | None = None, model_id: str | None = None
) -> ModelInference:
    """Create a WatsonX model inference instance with dependency injection.

    Args:
        settings: Settings object containing WatsonX configuration
        generate_params: Optional generation parameters
        model_id: Optional model ID override

    Returns:
        ModelInference: Configured WatsonX model inference instance
    """

    model_id = model_id or settings.rag_llm

    api_client = get_wx_client(settings)

    if generate_params is None:
        generate_params = {
            GenParams.MAX_NEW_TOKENS: settings.max_new_tokens,
            GenParams.MIN_NEW_TOKENS: settings.min_new_tokens,
            GenParams.TEMPERATURE: settings.temperature,
            GenParams.TOP_K: settings.top_k,
            GenParams.RANDOM_SEED: settings.random_seed,
        }

    model_inference = ModelInference(
        persistent_connection=True,
        model_id=model_id,
        params=generate_params,
        credentials=Credentials(api_key=settings.wx_api_key, url=settings.wx_url),
        project_id=settings.wx_project_id,
    )
    model_inference.set_api_client(api_client=api_client)
    return model_inference


def get_wx_embeddings_client(settings: Settings, embed_params: dict | None = None) -> wx_Embeddings:
    """Create a WatsonX embeddings client with dependency injection.

    Args:
        settings: Settings object containing WatsonX configuration
        embed_params: Optional embedding parameters

    Returns:
        wx_Embeddings: Configured WatsonX embeddings client
    """
    if embed_params is None:
        # Use WatsonX intelligent default token limits instead of aggressive truncation
        # Previous: TRUNCATE_INPUT_TOKENS: 3 destroyed semantic meaning (12 tokens → 3 tokens)
        # Result: Wrong embeddings and incorrect chunk retrieval in RAG search
        embed_params = {
            EmbedParams.RETURN_OPTIONS: {"input_text": True},
        }
    load_dotenv(override=True)
    return wx_Embeddings(
        persistent_connection=True,
        model_id=settings.embedding_model,
        params=embed_params,
        project_id=settings.wx_project_id,
        credentials=Credentials(api_key=settings.wx_api_key, url=settings.wx_url),
    )


def _log_embedding_generation(
    texts: list[str], settings: Settings, stage: str, embeddings: EmbeddingsList | None = None
) -> None:
    """
    Log embedding generation details for debugging.

    Args:
        texts: Input texts being embedded
        settings: Settings object with WatsonX configuration
        stage: "BEFORE" or "AFTER" embedding generation
        embeddings: Optional generated embeddings (only for AFTER stage)
    """
    try:
        import os
        from datetime import datetime

        debug_dir = "/tmp/rag_debug"
        os.makedirs(debug_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_file = f"{debug_dir}/embedding_generation_{stage.lower()}_{timestamp}.txt"

        with open(debug_file, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write(f"EMBEDDING GENERATION - {stage}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write("=" * 80 + "\n\n")

            f.write("INPUT TEXT(S):\n")
            f.write("-" * 80 + "\n")
            for i, text in enumerate(texts):
                f.write(f"Text {i + 1}: {text[:200]}{'...' if len(text) > 200 else ''}\n")
            f.write("\n")

            f.write("WATSONX CONFIGURATION:\n")
            f.write("-" * 80 + "\n")
            f.write(f"Embedding Model: {settings.embedding_model}\n")
            f.write(f"Embedding Dimension: {settings.embedding_dim}\n")
            f.write(f"Project ID: {settings.wx_project_id[:20]}...\n")
            f.write(f"API URL: {settings.wx_url}\n\n")

            if embeddings is not None and stage == "AFTER":
                f.write("GENERATED EMBEDDINGS:\n")
                f.write("-" * 80 + "\n")
                for i, embedding in enumerate(embeddings):
                    f.write(f"\nEmbedding {i + 1}:\n")
                    f.write(f"  Dimension: {len(embedding)}\n")
                    f.write(f"  First 10 values: {embedding[:10]}\n")
                    f.write(f"  Last 10 values: {embedding[-10:]}\n")
                    f.write(f"  Mean: {sum(embedding) / len(embedding):.6f}\n")
                    f.write(f"  Min: {min(embedding):.6f}\n")
                    f.write(f"  Max: {max(embedding):.6f}\n")
                f.write("\n")

            f.write("=" * 80 + "\n")
            f.write(f"END OF EMBEDDING GENERATION LOG - {stage}\n")
            f.write("=" * 80 + "\n")

        logger.info("📝 Embedding generation (%s) logged to: %s", stage, debug_file)

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.warning("Failed to log embedding generation (%s): %s", stage, e)


def get_embeddings(
    texts: str | list[str], settings: Settings = get_settings(), embed_client: wx_Embeddings | None = None
) -> EmbeddingsList:
    """
    Get embeddings for a given text or a list of texts with dependency injection.

    Args:
        texts: A single string or a list of strings
        settings: Settings object containing WatsonX configuration
        embed_client: Optional pre-configured embeddings client

    Returns:
        EmbeddingsList: A list of embedding vectors
    """

    if embed_client is None:
        embed_client = get_wx_embeddings_client(settings)

    # Ensure texts is a list
    if isinstance(texts, str):
        texts = [texts]

    # Optional debug logging - enable with RAG_DEBUG_EMBEDDINGS=1
    if os.getenv("RAG_DEBUG_EMBEDDINGS", "0") == "1":
        _log_embedding_generation(texts, settings, "BEFORE")

    try:
        # WatsonX embed_documents returns list[list[float]] but mypy sees it as Any
        # We know the actual return type from the library documentation
        embedding_vectors = embed_client.embed_documents(texts=texts, concurrency_limit=8)
        # Explicitly type the result as EmbeddingsList
        result: EmbeddingsList = embedding_vectors

        # Optional debug logging - enable with RAG_DEBUG_EMBEDDINGS=1
        if os.getenv("RAG_DEBUG_EMBEDDINGS", "0") == "1":
            _log_embedding_generation(texts, settings, "AFTER", result)

        return result
    except Exception as e:
        logging.error(f"get_embeddings failed {e}")
        raise e


def get_tokenization(texts: str | list[str], settings: Settings | None = None) -> list[list[str]]:
    """
    Get tokenization for a given text or a list of texts.

    :param texts: A single string or a list of strings.
    :param settings: Optional settings object. If None, uses get_settings()
    :return: A list of lists of strings representing the tokens.
    """
    if settings is None:
        settings = get_settings()

    wx_model = get_model(settings=settings)
    # Ensure texts is a list
    if isinstance(texts, str):
        texts = [texts]

    all_tokens = []

    try:
        for text in texts:
            tokens = wx_model.tokenize(prompt=text, return_tokens=True)
            all_tokens.append(tokens.get("result").get("tokens"))
    except Exception as e:
        logging.error(f"Error getting tokenization: {e}")
    finally:
        wx_model.close_persistent_connection()
    return all_tokens


@lru_cache(maxsize=128)
def extract_entities(text: str, wx_model: ModelInference | None = None, settings: Settings | None = None) -> list[dict]:
    if settings is None:
        settings = get_settings()

    if wx_model is None:
        wx_model = get_model(settings=settings)

    prompt = (
        "Extract the named entities from the following text and respond ONLY with a JSON list of dictionaries. Each dictionary should have 'entity' and 'type' keys, and nothing else.\n"
        "Example: [{'entity': 'New York', 'type': 'location'}, {'entity': 'IBM', 'type': 'organization'}]\n"
        f"Text: {text}"
    )

    try:
        response = generate_text(prompt, wx_model, settings=settings)

        # Ensure response is a string for processing
        if isinstance(response, list):
            response = response[0] if response else ""

        # Find the start and end of the JSON list
        start = response.find("[")
        end = response.rfind("]")
        if start != -1 and end != -1 and start < end:
            json_str = response[start : end + 1]
            logger.debug(f"Parsing JSON: {json_str}")
            entities = json.loads(json_str)
            cleaned_entities = clean_entities(entities)
            return cleaned_entities
        else:
            logger.warning(f"No JSON list found in response: {response}")
            return []
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse JSON response: {response}. Error: {e}")
        return []
    except Exception as e:
        logger.error(f"Error extracting entities: {e}")
        return []


def clean_entities(entities: list[dict]) -> list[dict]:
    cleaned = []
    for entity in entities:
        if isinstance(entity, dict) and "entity" in entity and "type" in entity:
            cleaned.append(entity)
    return cleaned


def get_tokenization_and_embeddings(
    texts: str | list[str], settings: Settings | None = None
) -> tuple[list[list[str]], EmbeddingsList]:
    """
    Get both tokenization and embeddings for a given text or a list of texts.

    :param texts: A single string or a list of strings.
    :param settings: Optional settings object. If None, uses get_settings()
    :return: A tuple containing a list of lists of strings (tokens) and a list of floats (embeddings).
    """
    if settings is None:
        settings = get_settings()

    tokenized_texts = get_tokenization(texts, settings=settings)
    embeddings = get_embeddings(texts, settings=settings)
    return tokenized_texts, embeddings


def save_embeddings_to_file(embeddings: EmbeddingsList, file_path: str, file_format: str = "json") -> None:
    """
    Save embeddings to a file.

    Args:
        embeddings (Embeddings): The list of embeddings to save.
        file_path (str): The path to the output file.
        file_format (str): The file format ("json" or "txt").

    Raises:
        ValueError: If an unsupported file format is provided.
    """
    if file_format not in {"json", "txt"}:
        raise ValueError(f"Unsupported file format: {file_format}")

    try:
        if file_format == "json":
            with open(file_path, "w") as f:
                json.dump(embeddings, f)
        elif file_format == "txt":
            with open(file_path, "w") as f:
                for embedding in embeddings:
                    f.write(" ".join(map(str, embedding)) + "\n")
        logging.info(f"Saved embeddings to file '{file_path}' in format '{file_format}'")
    except Exception as e:
        logging.error(f"Failed to save embeddings to file '{file_path}': {e}")
        raise


class ChromaEmbeddingFunction(EmbeddingFunction):
    def __init__(self, *, parameters: dict, model_id: str | None = None, settings: Settings = get_settings()) -> None:
        self._model_id = model_id
        self._parameters = parameters
        self._settings = settings
        self._client = get_wx_client(self._settings)

    def __call__(self, inputs: Documents) -> EmbeddingsList:  # type: ignore[override]
        return get_embeddings(texts=inputs, settings=self._settings)


def generate_text(
    prompt: str | list[str],
    wx_model: ModelInference | None = None,
    concurrency_limit: int = 10,
    params: dict | None = None,
    settings: Settings | None = None,
) -> str | list[str]:
    """Generate text using the WatsonX model.

    Args:
        prompt: Single prompt string or list of prompts for batch processing
        wx_model: Optional model instance, will create new one if not provided
        concurrency_limit: Max concurrent requests (default 10)
        params: Generation parameters

    Returns:
        Generated text(s) - string for single prompt, list for batch
    """
    try:
        logging.info("Making API call to text generation service")
        if wx_model is None:
            if settings is None:
                settings = get_settings()
            wx_model = get_model(settings, params, None)

        response = wx_model.generate_text(prompt=prompt, concurrency_limit=concurrency_limit, params=params)

        # Handle batch responses
        if isinstance(prompt, list):
            if isinstance(response, dict) and "results" in response:
                return [r["generated_text"].strip() for r in response["results"]]
            elif isinstance(response, list):
                return [r.strip() if isinstance(r, str) else r["generated_text"].strip() for r in response]
            else:
                logger.error(f"Unexpected response type: {type(response)}")
                raise ValueError(f"Unexpected response type: {type(response)}")

        # Handle single response
        if isinstance(response, dict):
            if "results" in response:
                return response["results"][0]["generated_text"].strip()  # type: ignore[no-any-return]
            elif "generated_text" in response:
                return response["generated_text"].strip()  # type: ignore[no-any-return]

        return response.strip() if isinstance(response, str) else response["generated_text"].strip()

    except Exception as e:
        logger.error("Error generating text: %s", str(e))
        raise


async def agenerate_responses(
    prompts: list[str],
    concurrency_level: int,
    wx_model: ModelInference | None = None,
    settings: Settings | None = None,
) -> list[str]:
    if settings is None:
        settings = get_settings()

    if wx_model is None:
        wx_model = get_model(settings=settings)

    async def throttled_agenerate(prompt: str, semaphore: asyncio.Semaphore, wx_mdl: ModelInference) -> str:
        async with semaphore:
            response = await wx_mdl.agenerate(prompt=prompt)
            return response.get("results")[0].get("generated_text").strip()  # type: ignore[no-any-return]

    semaphore = asyncio.Semaphore(value=concurrency_level)
    results = await asyncio.gather(*[throttled_agenerate(prompt, semaphore, wx_model) for prompt in prompts])
    return results


async def generate_all_responses(
    prompts: list[str],
    wx_model: ModelInference,
    concurrency_level: int = 5,
    settings: Settings | None = None,
) -> list[str]:
    return await agenerate_responses(prompts, concurrency_level=concurrency_level, wx_model=wx_model, settings=settings)


def generate_batch(
    prompts: list[str],
    wx_model: ModelInference | None = None,
    concurrency_level: int = 5,
    settings: Settings | None = None,
) -> list[str]:
    if settings is None:
        settings = get_settings()

    if wx_model is None:
        wx_model = get_model(settings=settings)
    return asyncio.run(generate_all_responses(prompts, wx_model, concurrency_level, settings))


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=30),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(Exception),
)
def generate_text_stream(
    prompt: str,
    model_id: str,
    max_tokens: int = 1024,
    temperature: float = 0.7,
    timeout: int = 30,
    random_seed: int = 50,
    max_retries: int = 3,
    settings: Settings | None = None,
) -> Generator[Any, None, None]:
    if settings is None:
        settings = get_settings()

    logging.info(
        f"Generating text with parameters: max_tokens={max_tokens}, temperature={temperature}, timeout={timeout}, max_retries={max_retries}"
    )
    logging.debug(f"Prompt: {prompt[:100]}...")  #
    model_inference = get_model(
        generate_params={
            GenParams.MAX_NEW_TOKENS: max_tokens,
            GenParams.TEMPERATURE: temperature,
            GenParams.RANDOM_SEED: random_seed,
        },
        model_id=model_id,
        settings=settings,
    )
    return model_inference.generate_text_stream(prompt=prompt)  # type: ignore[no-any-return]
