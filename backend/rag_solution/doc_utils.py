import uuid
from typing import Optional

from backend.vectordbs.data_types import Document, DocumentChunk
from backend.vectordbs.utils.watsonx import get_embeddings


def get_document(name: str, document_id: str, text: str) -> Document:
    """
    Create a Document object with embedded vectors.

    Args:
        name (str): The name of the document.
        document_id (str): The unique identifier for the document.
        text (str): The text content of the document.

    Returns:
        Document: A Document object with embedded vectors.
    """
    return Document(
        name=name,
        document_id=document_id,
        chunks=[
            DocumentChunk(
                chunk_id=str(uuid.uuid4()),
                text=text,
                vectors=get_embeddings(text),
                document_id=document_id,
            )
        ],
    )


def clean_text(text: Optional[str]) -> str:
    """
    Clean and normalize text by removing special characters and extra whitespace.

    Args:
        text (Optional[str]): The input text to clean.

    Returns:
        str: The cleaned and normalized text.
    """
    if text is None:
        return ""
    # Remove special characters and extra whitespace
    cleaned_text = "".join(char for char in text if char.isalnum() or char.isspace())
    cleaned_text = " ".join(cleaned_text.split())
    return cleaned_text
