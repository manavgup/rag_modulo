import json
import logging
import asyncio
from typing import List, Optional, Union, Tuple, Generator, Dict
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from functools import lru_cache
from chromadb.api.types import Documents, EmbeddingFunction
from dotenv import load_dotenv
from ibm_watsonx_ai import APIClient,Credentials
from ibm_watsonx_ai.metanames import EmbedTextParamsMetaNames as EmbedParams
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams
from ibm_watsonx_ai.foundation_models import ModelInference, Embeddings as wx_Embeddings

from core.config import settings
from ..data_types import Embeddings


WATSONX_INSTANCE_ID = settings.wx_project_id
EMBEDDING_MODEL = settings.embedding_model

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global client
client = None
embeddings_client = None


# Rate limiting settings
RATE_LIMIT = 10  # maximum number of requests per minute
RATE_LIMIT_PERIOD = 60  # in seconds

# Timestamp of the last API call
last_api_call = 0


def sublist(inputs: List, n: int) -> Generator[List, None, None]:
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

def _get_client() -> APIClient:
    global client
    if client is None:
        load_dotenv(override=True)
        client = APIClient(
            project_id=WATSONX_INSTANCE_ID,
            credentials=Credentials(api_key=settings.wx_api_key, url=settings.wx_url),
        )
    return client


def get_model(
    generate_params: Optional[Dict] = None, model_id: str = settings.rag_llm
) -> ModelInference:
    api_client = _get_client()

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
        project_id=WATSONX_INSTANCE_ID,
    )
    model_inference.set_api_client(api_client=api_client)
    return model_inference


def _get_embeddings_client(embed_params: Optional[Dict] = None) -> wx_Embeddings:
    global embeddings_client
    if embeddings_client is None:
        embed_params = {
            EmbedParams.TRUNCATE_INPUT_TOKENS: 256,
            EmbedParams.RETURN_OPTIONS: {"input_text": True},
        }
    if embeddings_client is None:
        load_dotenv(override=True)
        embeddings_client = wx_Embeddings(
            persistent_connection=True,
            model_id=EMBEDDING_MODEL,
            params=embed_params,
            project_id=WATSONX_INSTANCE_ID,
            credentials=Credentials(api_key=settings.wx_api_key, url=settings.wx_url),
        )
    return embeddings_client


def get_embeddings(texts: Union[str | List[str]],embed_client: Optional[wx_Embeddings]=None) -> Embeddings:
    """
    Get embeddings for a given text or a list of texts.

    :param texts: A single string or a list of strings.
    :param embed_client: an instance of watsonx embeddings model client.
    :return: A list of floats representing the embeddings.
    """
    if embed_client is None:
        embed_client = _get_embeddings_client()
    # Ensure texts is a list
    if isinstance(texts, str):
        texts = [texts]
    try:
        embedding_vectors = embed_client.embed_documents(texts=texts, concurrency_limit=10)
    except Exception as e:
        logging.error(f"get_embeddings failed {e}")
        raise e
    return embedding_vectors


def get_tokenization(texts: Union[str, List[str]]) -> List[List[str]]:
    """
    Get tokenization for a given text or a list of texts.

    :param texts: A single string or a list of strings.
    :return: A list of lists of strings representing the tokens.
    """
    wx_model = get_model()
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
def extract_entities(text: str, wx_model: Optional[ModelInference] = None) -> List[Dict]:
    if wx_model is None:
        wx_model = get_model()
    
    prompt = (
        "Extract the named entities from the following text and respond ONLY with a JSON list of dictionaries. Each dictionary should have 'entity' and 'type' keys, and nothing else.\n"
        "Example: [{'entity': 'New York', 'type': 'location'}, {'entity': 'IBM', 'type': 'organization'}]\n"
        f"Text: {text}"
    )
    
    try:
        response = generate_text(prompt, wx_model)
        
        # Find the start and end of the JSON list
        start = response.find('[')
        end = response.rfind(']')
        if start != -1 and end != -1 and start < end:
            json_str = response[start:end+1]
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

def clean_entities(entities: List[Dict]) -> List[Dict]:
    cleaned = []
    for entity in entities:
        if isinstance(entity, dict) and 'entity' in entity and 'type' in entity:
            cleaned.append(entity)
    return cleaned


def get_tokenization_and_embeddings(
    texts: Union[str, List[str]]
) -> Tuple[List[List[str]], Embeddings]:
    """
    Get both tokenization and embeddings for a given text or a list of texts.

    :param texts: A single string or a list of strings.
    :return: A tuple containing a list of lists of strings (tokens) and a list of floats (embeddings).
    """
    tokenized_texts = get_tokenization(texts)
    embeddings = get_embeddings(texts)
    return tokenized_texts, embeddings


def save_embeddings_to_file(
    embeddings: Embeddings, file_path: str, file_format: str = "json"
):
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
        logging.info(
            f"Saved embeddings to file '{file_path}' in format '{file_format}'"
        )
    except Exception as e:
        logging.error(f"Failed to save embeddings to file '{file_path}': {e}")
        raise


class ChromaEmbeddingFunction(EmbeddingFunction):
    def __init__(
        self,
        *,
        parameters: Dict,
        model_id: Optional[str] = settings.rag_llm,
    ):
        self._model_id = model_id
        self._parameters = parameters
        self._client = _get_client()

    def __call__(self, inputs: Documents) -> Embeddings:
        return get_embeddings(texts=inputs)


def generate_text(prompt: Union[str, List[str]], wx_model: Optional[ModelInference] = None,
                  concurrency_limit: int = 10, params: Optional[Dict] = None) -> Union[str, List[str]]:
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
            wx_model = get_model()
        
        response = wx_model.generate_text(prompt=prompt, concurrency_limit=concurrency_limit)

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
        logger.error("Error generating text: %s", str(e))
        raise


async def agenerate_responses(
    prompts: List[str],
    concurrency_level: int,
    wx_model: Optional[ModelInference] = None,
) -> List:

    if wx_model is None:
        wx_model = get_model()

    async def throttled_agenerate(
        prompt: str, semaphore: asyncio.Semaphore, wx_mdl: ModelInference
    ):
        async with semaphore:
            response = await wx_mdl.agenerate(prompt=prompt)
            return response.get("results")[0].get("generated_text").strip()

    semaphore = asyncio.Semaphore(value=concurrency_level)
    results = await asyncio.gather(
        *[throttled_agenerate(prompt, semaphore, wx_model) for prompt in prompts]
    )
    return results


async def generate_all_responses(
    prompts: List[str],
    wx_model: ModelInference,
    concurrency_level: int = 5,
) -> List:
    return await agenerate_responses(
        prompts, concurrency_level=concurrency_level, wx_model=wx_model
    )


def generate_batch(
    prompts: List[str],
    wx_model: Optional[ModelInference] = None,
    concurrency_level: int = 5,
) -> List:
    if wx_model is None:
        wx_model = get_model()
    return asyncio.run(generate_all_responses(prompts, wx_model, concurrency_level))


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=30),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(Exception),
)
def generate_text_stream(
    prompt: str,
    model_id: str,
    max_tokens: int = 150,
    temperature: float = 0.7,
    timeout: int = 30,
    random_seed: int = 50,
    max_retries: int = 3,
) -> Generator:

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
    )
    return model_inference.generate_text_stream(prompt=prompt)
