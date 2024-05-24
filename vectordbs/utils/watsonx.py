import logging
from dataclasses import abc
from dotenv import load_dotenv
from genai import Client, Credentials
from genai.text.generation import CreateExecutionOptions
from genai.schema import TextEmbeddingParameters
from typing import List, Union

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
