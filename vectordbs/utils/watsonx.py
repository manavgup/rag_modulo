import logging
from dotenv import load_dotenv
from genai import Client, Credentials
from genai.text.generation import CreateExecutionOptions
from genai.schema import TextEmbeddingParameters
from typing import List, Union, Optional
import json
from vectordbs.data_types import Embeddings
from chromadb.api.types import EmbeddingFunction, Documents

EMBEDDING_MODEL="sentence-transformers/all-minilm-l6-v2"

def init_credentials() -> Client:
    client = None
    load_dotenv(override=True)
    creds = Credentials.from_env()
    if creds.api_endpoint:
        logging.info(f"Your API endpoint is: {creds.api_endpoint}")
    client = Client(credentials=creds)
    return client

def get_embeddings(texts: Union[str | List[str]]) -> List[float]:
    """
    Get embeddings for a given text or a list of texts.
    
    :param texts: A single string or a list of strings.
    :return: A list of floats representing the embeddings.
    """
    embeddings: List[float] = []
    client = init_credentials()
    
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
                embeddings.extend(result) # flatten each result
    except Exception as e:
        logging.error(e)
        
    return embeddings

def save_embeddings_to_file(embeddings: Embeddings, file_path: str, file_format: str = "json"):
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
    def __init__(self, *, model_id: str, 
                 parameters: Optional[TextEmbeddingParameters] = None):
        self._model_id = model_id
        self._parameters = parameters
        self._client = init_credentials()
        
    def __call__(self, inputs: Documents) -> Embeddings:
        embeddings: Embeddings = []
        for response in self._client.text.embedding.create(
            model_id=self._model_id, inputs=inputs, parameters=self._parameters
        ):
            embeddings.extend(response.results)

        return embeddings