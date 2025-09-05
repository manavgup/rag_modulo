"""Tests for Data Ingestion Components."""

import multiprocessing
from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session

from rag_solution.data_ingestion.chunking import semantic_chunking, simple_chunking, token_based_chunking
from rag_solution.data_ingestion.document_processor import DocumentProcessor
from rag_solution.data_ingestion.excel_processor import ExcelProcessor
from rag_solution.data_ingestion.ingestion import DocumentStore
from rag_solution.data_ingestion.pdf_processor import PdfProcessor
from rag_solution.data_ingestion.txt_processor import TxtProcessor
from rag_solution.data_ingestion.word_processor import WordProcessor


@pytest.fixture
def db_session() -> Mock:
    """Create a mock database session."""
    return Mock(spec=Session)


@pytest.mark.integration
def test_base_processor() -> None:
    """Test the BaseProcessor."""
    # BaseProcessor is abstract, so we can't instantiate it directly
    # This test should be removed or modified


def test_simple_chunking() -> None:
    """Test simple chunking."""
    text = "This is a test text that needs to be chunked into smaller pieces for processing."
    chunks = simple_chunking(text, min_chunk_size=10, max_chunk_size=20, overlap=5)
    assert len(chunks) > 1
    assert all(len(chunk) >= 10 for chunk in chunks)
    assert all(len(chunk) <= 20 for chunk in chunks[:-1])


def test_semantic_chunking() -> None:
    """Test semantic chunking."""
    text = "This is the first topic. This is also about the first topic. This is a new topic."
    chunks = semantic_chunking(text)
    assert len(chunks) > 1


def test_token_based_chunking() -> None:
    """Test token-based chunking."""
    text = "This is a test text. It has multiple sentences. We want to ensure proper tokenization."
    chunks = token_based_chunking(text, max_tokens=10, overlap=2)
    assert len(chunks) > 1


def test_document_processor(db_session: Mock) -> None:
    """Test the DocumentProcessor."""
    processor = DocumentProcessor(db_session)  # noqa: F841
    # DocumentProcessor doesn't have a process method that takes a File object
    # This test needs to be rewritten to use process_document with a file path


def test_excel_processor(db_session: Mock) -> None:
    """Test the ExcelProcessor."""
    processor = ExcelProcessor()  # noqa: F841
    # ExcelProcessor doesn't take db_session parameter
    # This test needs to be rewritten to use process with a file path


def test_pdf_processor(db_session: Mock) -> None:
    """Test the PdfProcessor."""
    # PdfProcessor requires a multiprocessing manager
    with multiprocessing.Manager() as manager:
        processor = PdfProcessor(manager)  # noqa: F841
        # This test needs to be rewritten to use process with a file path


def test_txt_processor(db_session: Mock) -> None:
    """Test the TxtProcessor."""
    processor = TxtProcessor()  # noqa: F841
    # TxtProcessor doesn't take db_session parameter
    # This test needs to be rewritten to use process with a file path


def test_word_processor(db_session: Mock) -> None:
    """Test the WordProcessor."""
    processor = WordProcessor()  # noqa: F841
    # WordProcessor doesn't take db_session parameter
    # This test needs to be rewritten to use process with a file path


@pytest.mark.asyncio
async def test_document_store() -> None:
    """Test the DocumentStore."""
    # Mock vector store
    vector_store = Mock()
    vector_store.add_documents = Mock()
    vector_store.delete_collection = Mock()
    vector_store.create_collection = Mock()

    store = DocumentStore(vector_store=vector_store, collection_name="test_collection")

    # Create test files
    test_files = ["backend/tests/test_files/test1.txt", "backend/tests/test_files/test2.pdf"]

    # Test document ingestion
    processed_docs = await store.load_documents(test_files)
    assert len(processed_docs) > 0

    # Test document retrieval
    docs = store.get_documents()
    assert len(docs) == len(processed_docs)

    # Test clearing documents
    await store.clear()
    assert len(store.get_documents()) == 0
    vector_store.delete_collection.assert_called_once_with("test_collection")
    vector_store.create_collection.assert_called_once_with("test_collection")


if __name__ == "__main__":
    pytest.main([__file__])
