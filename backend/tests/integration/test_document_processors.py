"""Tests for Document Processing Components."""

import multiprocessing
import os
from collections.abc import Generator
from datetime import datetime
from typing import Any

import pandas as pd  # type: ignore[import-untyped]
import pymupdf  # type: ignore[import-untyped]  # type: ignore[import-not-found]
import pytest

from core.custom_exceptions import DocumentProcessingError
from rag_solution.data_ingestion.document_processor import DocumentProcessor
from rag_solution.data_ingestion.excel_processor import ExcelProcessor
from rag_solution.data_ingestion.pdf_processor import PdfProcessor
from rag_solution.data_ingestion.txt_processor import TxtProcessor
from rag_solution.data_ingestion.word_processor import WordProcessor
from vectordbs.data_types import Document

# Mapping of processor types to their classes
PROCESSOR_CONFIGS = {
    "txt": {"class": TxtProcessor, "fixture": "test_txt_path"},
    "pdf": {"class": PdfProcessor, "fixture": "test_pdf_path"},
    "word": {"class": WordProcessor, "fixture": "test_word_path"},
    "excel": {"class": ExcelProcessor, "fixture": "test_excel_path"},
}


# Fixtures for Test Files
@pytest.fixture(scope="function")
def sample_excel_path() -> Generator[str, None, None]:
    """Create a sample Excel file for testing."""
    file_path = "/tmp/test_data.xlsx"

    # Create test data
    df1 = pd.DataFrame({"Column1": ["Data1", "Data2", "Data3"], "Column2": [1, 2, 3], "Column3": ["A", "B", "C"]})

    df2 = pd.DataFrame({"Name": ["John", "Jane", "Bob"], "Age": [25, 30, 35], "City": ["New York", "London", "Paris"]})

    with pd.ExcelWriter(file_path) as writer:
        df1.to_excel(writer, sheet_name="Sheet1", index=False)
        df2.to_excel(writer, sheet_name="Sheet2", index=False)

    yield file_path

    if os.path.exists(file_path):
        os.remove(file_path)


# Base Test Class
@pytest.mark.integration
class TestDocumentProcessors:
    """Consolidated test class for all document processors."""

    @pytest.fixture(params=PROCESSOR_CONFIGS.keys())
    def processor_type(self: Any, request: Any) -> str:
        """Parametrized fixture that provides each processor type."""
        return str(request.param)  # type: ignore[no-any-return]

    @pytest.fixture
    def processor(self: Any, processor_type: str) -> Any:
        """Dynamic fixture that returns the appropriate processor instance."""
        processor_class = PROCESSOR_CONFIGS[processor_type]["class"]
        if processor_type == "pdf":
            with multiprocessing.Manager() as manager:
                return processor_class(manager)  # type: ignore[operator,no-any-return]
        return processor_class()  # type: ignore[operator,no-any-return]

    @pytest.mark.asyncio
    async def test_basic_processing(self, processor: Any, request: Any, processor_type: str) -> None:
        """Test basic document processing for all processor types."""
        fixture_name = PROCESSOR_CONFIGS[processor_type]["fixture"]
        test_file = request.getfixturevalue(fixture_name)

        docs = []
        async for document in processor.process(test_file):
            docs.append(document)

        assert len(docs) > 0
        assert all(isinstance(doc, Document) for doc in docs)
        assert docs[0].name == os.path.basename(str(test_file))
        assert len(docs[0].chunks) > 0

    @pytest.mark.asyncio
    async def test_error_handling(self, processor: Any, test_non_existent_pdf_path: str) -> None:
        """Test error handling for non-existent files."""
        with pytest.raises(DocumentProcessingError):
            async for _ in processor.process(test_non_existent_pdf_path):
                pass

    # Excel-specific tests
    class TestExcelProcessor:
        """Excel-specific test cases."""

        @pytest.mark.asyncio
        async def test_multiple_sheets(self, sample_excel_path: str) -> None:
            processor = ExcelProcessor()
            documents = []
            async for doc in processor.process(sample_excel_path, "test_doc_id"):
                documents.append(doc)

            all_text = " ".join(" ".join(chunk.text for chunk in doc.chunks) for doc in documents)
            assert "Sheet: Sheet1" in all_text
            assert "Sheet: Sheet2" in all_text
            assert "Column1" in all_text and "Name" in all_text

        @pytest.mark.asyncio
        async def test_special_characters(self) -> None:
            special_file = "/tmp/special.xlsx"
            df = pd.DataFrame(
                {
                    "Column1": ["Data with \n newline", "Data with \t tab", "Data with 🌟 emoji"],
                    "Column2": ['Data with "quotes"', "Data with 'single quotes'", "Data with &<>"],
                }
            )

            df.to_excel(special_file, index=False)

            processor = ExcelProcessor()
            documents = []
            async for doc in processor.process(special_file, "test_doc_id"):
                documents.append(doc)

            all_text = " ".join(" ".join(chunk.text for chunk in doc.chunks) for doc in documents)
            assert "newline" in all_text
            assert "tab" in all_text
            assert "emoji" in all_text

            os.remove(special_file)

    # PDF-specific tests
    class TestPdfProcessor:
        """PDF-specific test cases."""

        def test_text_extraction(self, complex_test_pdf_path: str) -> None:
            with multiprocessing.Manager() as manager:
                processor = PdfProcessor(manager)
                with pymupdf.open(str(complex_test_pdf_path)) as doc:
                    page1_content = processor.extract_text_from_page(doc[0])
                    assert any("This is a test document." in block["content"] for block in page1_content if block["type"] == "text")

        def test_table_validation(self) -> None:
            with multiprocessing.Manager() as manager:
                processor = PdfProcessor(manager)
                valid_table = [
                    ["Header 1", "Header 2", "Header 3"],
                    ["Data 1", "Data 2", "Data 3"],
                    ["Data 4", "Data 5", "Data 6"],
                ]
                assert processor._is_likely_table(valid_table)
                assert not processor._is_likely_table([])
                assert not processor._is_likely_table([["Single"]])

        @pytest.mark.asyncio
        async def test_metadata_inheritance(self, complex_test_pdf_path: str) -> None:
            with multiprocessing.Manager() as manager:
                processor = PdfProcessor(manager)
                processed_docs = []
                async for doc in processor.process(str(complex_test_pdf_path), "test_id"):
                    processed_docs.append(doc)

                assert len(processed_docs) > 0
                doc = processed_docs[0]
                assert doc.metadata is not None
                assert doc.metadata.document_name == os.path.basename(str(complex_test_pdf_path))
                assert isinstance(doc.metadata.creation_date, datetime)


# Main Document Processor Tests
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fixture_name",
    ["test_txt_path", "test_pdf_path", "test_word_path", "test_excel_path"],
)
async def test_document_processor(request: Any, fixture_name: str) -> None:
    """Test the main DocumentProcessor with different file types."""
    test_file = request.getfixturevalue(fixture_name)
    processor = DocumentProcessor()
    docs = []
    async for document in processor.process_document(test_file, "test_doc_id"):
        docs.append(document)

    assert len(docs) > 0
    assert all(isinstance(doc, Document) for doc in docs)
    assert len(docs[0].chunks) > 0


if __name__ == "__main__":
    pytest.main([__file__])
