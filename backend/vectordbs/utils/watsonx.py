import json
import logging
from typing import List, Optional, Union, Tuple

from chromadb.api.types import Documents, EmbeddingFunction
from dotenv import load_dotenv
from genai.client import Client
from genai.credentials import Credentials
from genai.schema import (TextEmbeddingParameters, 
                          TextGenerationParameters, 
                          TextTokenizationReturnOptions, 
                          TextTokenizationReturnOptions, 
                          TextTokenizationParameters)
from genai.text.generation import CreateExecutionOptions

from backend.core.config import settings
import logging
from ..data_types import Embeddings

EMBEDDING_MODEL = settings.embedding_model
TOKENIZATION_MODEL = "google/flan-t5-xl"  # You can change this to your preferred model

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global client
client = None

def _get_client() -> Client:
    global client
    if client is None:
        load_dotenv(override=True)
        creds = Credentials.from_env()
        client = Client(credentials=creds)
    return client

def get_embeddings(texts: Union[str | List[str]]) -> List[float]:
    """
    Get embeddings for a given text or a list of texts.

    :param texts: A single string or a list of strings.
    :return: A list of floats representing the embeddings.
    """
    embeddings: List[float] = []
    client = _get_client()

    # Ensure texts is a list
    if isinstance(texts, str):
        texts = [texts]
    try:
        for response in client.text.embedding.create(
            model_id=EMBEDDING_MODEL,
            inputs=texts,
            parameters=TextEmbeddingParameters(truncate_input_tokens=True),
            execution_options=CreateExecutionOptions(ordered=False),
        ):
            for result in response.results:
                embeddings.extend(result.embedding)  # assuming result is already a list of floats
    except Exception as e:
        logging.error(e)

    return embeddings

def get_tokenization(texts: Union[str, List[str]], batch_size: int = 100) -> List[List[str]]:
    """
    Get tokenization for a given text or a list of texts.

    :param texts: A single string or a list of strings.
    :param batch_size: The batch size for processing.
    :return: A list of lists of strings representing the tokens.
    """
    client = _get_client()
    
    # Ensure texts is a list
    if isinstance(texts, str):
        texts = [texts]

    all_tokens = []

    try:
        for response in client.text.tokenization.create(
            model_id=TOKENIZATION_MODEL,
            input=texts,
            execution_options=CreateExecutionOptions(
                batch_size=batch_size,
                ordered=True,
            ),
            parameters=TextTokenizationParameters(
                return_options=TextTokenizationReturnOptions(
                    tokens=True,
                )
            ),
        ):
            for result in response.results:
                all_tokens.append(result.tokens)
    except Exception as e:
        logging.error(f"Error getting tokenization: {e}")

    return all_tokens

def get_tokenization_and_embeddings(texts: Union[str, List[str]]) -> Tuple[List[List[str]], List[float]]:
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
        self, *, model_id: str, parameters: Optional[TextEmbeddingParameters] = None
    ):
        self._model_id = model_id
        self._parameters = parameters
        self._client = _get_client()

    def __call__(self, inputs: Documents) -> Embeddings:
        embeddings: Embeddings = []
        for response in self._client.text.embedding.create(
            model_id=self._model_id, inputs=inputs, parameters=self._parameters
        ):
            embeddings.extend(response.results)

        return embeddings


def generate_text(prompt: str, max_tokens: int = 150, temperature: float = 0.7) -> str:
    client = _get_client()
    try:
        response = client.text.generation.create(
            model_id="meta/llama3-8b-v1",
            input=prompt,
            parameters=TextGenerationParameters(max_new_tokens=max_tokens, temperature=temperature),
        )
        return response.results[0].generated_text.strip()
    except Exception as e:
        logging.error(f"Error generating text: {e}")
        return ""
