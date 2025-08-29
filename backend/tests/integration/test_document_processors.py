"""Tests for Document Processing Components."""

import multiprocessing
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import pymupdf
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
def sample_excel_path():
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


@pytest.fixture(scope="function")
def complex_test_pdf_path():
    """Fixture to create a robust PDF file with multiple pages, tables and images."""
    test_file = Path("/tmp/complex_test.pdf")

    doc = pymupdf.open()

    # Page 1: Text and Heading
    page1 = doc.new_page()
    page1.insert_text((100, 100), "This is a test document.")
    page1.insert_text((100, 150), "Heading 1", fontsize=14)
    page1.insert_text((100, 200), "This is some content under heading 1.")

    # Add more pages and content as needed
    # ... [Previous PDF creation code remains the same]

    doc.save(test_file)
    doc.close()

    yield test_file

    if test_file.exists():
        test_file.unlink()


# Base Test Class
class TestDocumentProcessors:
    """Consolidated test class for all document processors."""

    @pytest.fixture(params=PROCESSOR_CONFIGS.keys())
    def processor_type(self, request):
        """Parametrized fixture that provides each processor type."""
        return request.param

    @pytest.fixture
    def processor(self, processor_type):
        """Dynamic fixture that returns the appropriate processor instance."""
        processor_class = PROCESSOR_CONFIGS[processor_type]["class"]
        if processor_type == "pdf":
            with multiprocessing.Manager() as manager:
                return processor_class(manager)
        return processor_class()

    @pytest.mark.asyncio
    async def test_basic_processing(self, processor, request, processor_type):
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
    async def test_error_handling(self, processor, test_non_existent_pdf_path):
        """Test error handling for non-existent files."""
        with pytest.raises(DocumentProcessingError):
            async for _ in processor.process(test_non_existent_pdf_path):
                pass

    # Excel-specific tests
    class TestExcelProcessor:
        """Excel-specific test cases."""

        @pytest.mark.asyncio
        async def test_multiple_sheets(self, sample_excel_path):
            processor = ExcelProcessor()
            documents = []
            async for doc in processor.process(sample_excel_path):
                documents.append(doc)

            all_text = " ".join(doc.text for doc in documents)
            assert "Sheet: Sheet1" in all_text
            assert "Sheet: Sheet2" in all_text
            assert "Column1" in all_text and "Name" in all_text

        @pytest.mark.asyncio
        async def test_special_characters(self):
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
            async for doc in processor.process(special_file):
                documents.append(doc)

            all_text = " ".join(doc.text for doc in documents)
            assert "newline" in all_text
            assert "tab" in all_text
            assert "emoji" in all_text

            os.remove(special_file)

    # PDF-specific tests
    class TestPdfProcessor:
        """PDF-specific test cases."""

        def test_text_extraction(self, complex_test_pdf_path):
            with multiprocessing.Manager() as manager:
                processor = PdfProcessor(manager)
                with pymupdf.open(str(complex_test_pdf_path)) as doc:
                    page1_content = processor.extract_text_from_page(doc[0])
                    assert any(
                        "This is a test document." in block["content"]
                        for block in page1_content
                        if block["type"] == "text"
                    )

        def test_table_validation(self):
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
        async def test_metadata_inheritance(self, complex_test_pdf_path):
            with multiprocessing.Manager() as manager:
                processor = PdfProcessor(manager)
                processed_docs = []
                async for doc in processor.process(str(complex_test_pdf_path), "test_id"):
                    processed_docs.append(doc)

                assert len(processed_docs) > 0
                doc = processed_docs[0]
                assert doc.metadata.document_name == os.path.basename(str(complex_test_pdf_path))
                assert isinstance(doc.metadata.creation_date, datetime)


# Main Document Processor Tests
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fixture_name",
    ["test_txt_path", "test_pdf_path", "test_word_path", "test_excel_path"],
)
async def test_document_processor(request, fixture_name):
    """Test the main DocumentProcessor with different file types."""
    test_file = request.getfixturevalue(fixture_name)
    processor = DocumentProcessor()
    docs = []
    async for document in processor.process_document(test_file):
        docs.append(document)

    assert len(docs) > 0
    assert all(isinstance(doc, Document) for doc in docs)
    assert len(docs[0].chunks) > 0


if __name__ == "__main__":
    pytest.main([__file__])
