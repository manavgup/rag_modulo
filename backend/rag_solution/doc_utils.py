"""Document utilities.

This module provides utility functions for creating and manipulating
document objects, including text cleaning and validation.
"""

import logging
import os
import uuid

from vectordbs.data_types import Document, DocumentChunk, DocumentChunkMetadata, DocumentMetadata, Source


def _get_embeddings_for_doc_utils(text: str | list[str]) -> list[list[float]]:
    """
    Get embeddings using the provider-based approach with rate limiting.

    This is a utility function for doc_utils.py to access embedding functionality
    without requiring processor instantiation.

    Args:
        text: Single text string or list of text strings to embed

    Returns:
        List of embedding vectors

    Raises:
        LLMProviderError: If provider-related errors occur
        SQLAlchemyError: If database-related errors occur
        Exception: If other unexpected errors occur
    """
    # Import here to avoid circular imports
    from sqlalchemy.exc import SQLAlchemyError  # pylint: disable=import-outside-toplevel

    from core.custom_exceptions import LLMProviderError  # pylint: disable=import-outside-toplevel
    from rag_solution.file_management.database import create_session_factory  # pylint: disable=import-outside-toplevel
    from rag_solution.generation.providers.factory import LLMProviderFactory  # pylint: disable=import-outside-toplevel

    # Create session and get embeddings in one clean flow
    session_factory = create_session_factory()
    db = session_factory()

    try:
        factory = LLMProviderFactory(db)
        provider = factory.get_provider("watsonx")
        return provider.get_embeddings(text)
    except LLMProviderError as e:
        logging.error("LLM provider error during embedding generation: %s", e)
        raise
    except SQLAlchemyError as e:
        logging.error("Database error during embedding generation: %s", e)
        raise
    except Exception as e:
        logging.error("Unexpected error during embedding generation: %s", e)
        raise
    finally:
        db.close()


def get_document(name: str, document_id: str, text: str, metadata: dict | None = None) -> Document:
    """
    Create a Document object with embedded vectors.

    Args:
        name (str): The name of the document.
        document_id (str): The unique identifier for the document.
        text (str): The text content of the document.
        metadata (Optional[dict]): Additional metadata for the document.

    Returns:
        Document: A Document object with embedded vectors.

    Examples:
        >>> # Create a document without metadata
        >>> doc = get_document("sample.pdf", "doc123", "This is sample text")
        >>> doc.name
        'sample.pdf'
        >>> doc.document_id
        'doc123'
        >>> len(doc.chunks)
        1
        >>> doc.chunks[0].text
        'This is sample text'
        >>> doc.metadata is None
        True

        >>> # Create a document with custom metadata
        >>> metadata = {"author": "John Doe", "title": "Sample Article"}
        >>> doc = get_document("article.txt", "doc456", "Article content", metadata)
        >>> doc.metadata.author
        'John Doe'
        >>> doc.metadata.title
        'Sample Article'
        >>> doc.chunks[0].metadata.source
        <Source.OTHER: 'other'>
    """
    # Create chunk metadata for source information
    chunk_metadata = DocumentChunkMetadata(
        source=Source.PDF if name.lower().endswith(".pdf") else Source.OTHER, document_id=document_id
    )

    # Create document metadata if provided
    doc_metadata = None
    if metadata:
        doc_metadata = DocumentMetadata(**metadata)

    # Get embeddings using provider-based approach with rate limiting
    embeddings = _get_embeddings_for_doc_utils(text)

    return Document(
        name=name,
        document_id=document_id,
        chunks=[
            DocumentChunk(
                chunk_id=str(uuid.uuid4()),
                text=text,
                embeddings=embeddings[0],  # Extract first embedding from list
                document_id=document_id,
                metadata=chunk_metadata,
            )
        ],
        metadata=doc_metadata,
    )


def clean_text(text: str | None) -> str:
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


def extract_filename_from_path(file_path: str) -> str:
    """
    Extract the filename from a file path.

    Args:
        file_path (str): The full file path.

    Returns:
        str: The extracted filename without the path.

    Examples:
        >>> # Extract from simple filename
        >>> extract_filename_from_path("document.pdf")
        'document.pdf'

        >>> # Extract from relative path
        >>> extract_filename_from_path("folder/subfolder/file.txt")
        'file.txt'

        >>> # Extract from absolute path
        >>> extract_filename_from_path("/home/user/documents/report.docx")
        'report.docx'

        >>> # Extract from Windows path (use forward slashes)
        >>> extract_filename_from_path("C:/Users/User/Desktop/presentation.pptx")
        'presentation.pptx'

        >>> # Handle path with multiple dots
        >>> extract_filename_from_path("archive.tar.gz")
        'archive.tar.gz'
    """
    return os.path.basename(file_path)


def is_valid_document_type(filename: str, allowed_extensions: list[str]) -> bool:
    """
    Check if a filename has an allowed file extension.

    Args:
        filename (str): The filename to check.
        allowed_extensions (list[str]): List of allowed file extensions.

    Returns:
        bool: True if the file extension is allowed, False otherwise.

    Examples:
        >>> # Check PDF files
        >>> is_valid_document_type("document.pdf", [".pdf", ".txt"])
        True

        >>> # Check text files
        >>> is_valid_document_type("notes.txt", [".pdf", ".txt"])
        True

        >>> # Check unsupported files
        >>> is_valid_document_type("image.jpg", [".pdf", ".txt"])
        False

        >>> # Check case sensitivity (should be case-insensitive)
        >>> is_valid_document_type("Document.PDF", [".pdf", ".txt"])
        True

        >>> # Check files without extensions
        >>> is_valid_document_type("README", [".pdf", ".txt"])
        False

        >>> # Check empty allowed extensions
        >>> is_valid_document_type("file.txt", [])
        False
    """
    _, ext = os.path.splitext(filename)
    return ext.lower() in [ext.lower() for ext in allowed_extensions]


if __name__ == "__main__":
    # Run doctests when the module is executed directly
    import doctest

    doctest.testmod(verbose=True)
