from pymilvus import (
    connections,
    utility,
    FieldSchema, CollectionSchema, DataType,
    Collection
)
import PyPDF2
from typing import List, Optional, Union, Sequence
from genai.client import Client
from genai.credentials import Credentials
from genai.schema import TextEmbeddingParameters
from dotenv import load_dotenv

# make sure you have a .env file under genai root with
# GENAI_KEY=<your-genai-key>
# GENAI_API=<genai-api-endpoint>
load_dotenv()
credentials = Credentials.from_env()
client = Client(credentials=credentials)


def heading(text: str) -> str:
    """Helper function for centering text."""
    return "\n" + f" {text} ".center(80, "=") + "\n"


print(heading("List all models"))
for model in client.model.list(limit=100).results:
    print(model.model_dump(include=["name", "id"]))

for model in client.model.list(limit=100).results:
    print(heading("Get model detail"))
    model_detail = client.model.retrieve(model.id).result
    pprint(model_detail.model_dump(include=["name", "description", "id", "developer", "size"]))
