from typing import List, Union

from dotenv import load_dotenv
from genai.client import Client
from genai.credentials import Credentials
from genai.schema import TextEmbeddingParameters
from genai.text.embedding import CreateExecutionOptions

# make sure you have a .env file under genai root with
# GENAI_KEY=<your-genai-key>
# GENAI_API=<genai-api-endpoint>
load_dotenv()


def heading(text: str) -> str:
    """Helper function for centering text."""
    return "\n" + f" {text} ".center(80, "=") + "\n"


client = Client(credentials=Credentials.from_env())


def get_embeddings(texts: Union[str | List[str]]) -> List[float]:
    embeddings: List[float] = []
    try:
        for response in client.text.embedding.create(
            model_id="sentence-transformers/all-minilm-l6-v2",
            inputs=texts,
            parameters=TextEmbeddingParameters(truncate_input_tokens=True),
            execution_options=CreateExecutionOptions(ordered=False),
        ):
            for result in response.results:
                embeddings.extend(result)
                print("Embedding: ", result)
    except Exception as e:
        print("Error: ", e)
    return embeddings


inputs = ["Hello", "world"]
model_id = "sentence-transformers/all-minilm-l6-v2"

print(heading("Running embedding for inputs in parallel"))
# yields batch of results that are produced asynchronously and in parallel
get_embeddings(inputs)
