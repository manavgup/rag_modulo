import multiprocessing
import os
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

import pymupdf
import pytest

from core.custom_exceptions import DocumentProcessingError
from rag_solution.data_ingestion.pdf_processor import PdfProcessor
from vectordbs.data_types import DocumentChunk, DocumentChunkMetadata, Source


@pytest.fixture(scope="function")
def complex_test_pdf_path():
    """Fixture to create a robust PDF file with multiple pages, tables and images."""
    test_file = Path("/tmp/complex_test.pdf")

    # Create a PDF using PyMuPDF
    doc = pymupdf.open()

    # Page 1: Text and Heading
    page1 = doc.new_page()
    page1.insert_text((100, 100), "This is a test document.")
    page1.insert_text((100, 150), "Heading 1", fontsize=14)
    page1.insert_text((100, 200), "This is some content under heading 1.")

    # Page 2: Table 1
    page2 = doc.new_page()
    page2.insert_text((100, 100), "Table 1", fontsize=14)

    table_data = [
        ["Header 1", "Header 2", "Header 3"],
        ["Row 1, Col 1", "Row 1, Col 2", "Row 1, Col 3"],
        ["Row 2, Col 1", "Row 2, Col 2", "Row 2, Col 3"],
    ]

    draw_table(page2, table_data, 150, 100, 133, 30)

    # Page 3: Table 2 and Image
    page3 = doc.new_page()
    page3.insert_text((100, 100), "Table 2", fontsize=14)

    table2_data = [
        ["Header A", "Header B", "Header C"],
        ["Row 1, Col A", "Row 1, Col B", "Row 1, Col C"],
        ["Row 2, Col A", "Row 2, Col B", "Row 2, Col C"],
    ]

    draw_table(page3, table2_data, 150, 100, 133, 30)

    # Add an image
    img_rect = pymupdf.Rect(100, 300, 200, 400)
    page3.insert_image(img_rect, filename="backend/tests/test_files/test_image.png")

    # Page 4: Sparse table for validation testing
    page4 = doc.new_page()
    sparse_table_data = [["", ""], ["", ""], ["Single Data", ""]]
    draw_table(page4, sparse_table_data, 150, 100, 133, 30)

    # Page 5: Complex table layout
    page5 = doc.new_page()
    complex_table_data = [
        ["Product", "Q1 Sales", "Q2 Sales", "Q3 Sales", "Q4 Sales"],
        ["Widget A", "$1000", "$1200", "$1100", "$1300"],
        ["Widget B", "$800", "$850", "$900", "$950"],
        ["Widget C", "$1500", "$1600", "$1650", "$1700"],
    ]
    draw_table(page5, complex_table_data, 150, 100, 100, 30)

    # Page 6: Grid-like text layout
    page6 = doc.new_page()
    grid_text = [
        ["Item", "Price", "Quantity", "Total"],
        ["Apple", "$1.00", "5", "$5.00"],
        ["Orange", "$0.75", "8", "$6.00"],
        ["Banana", "$0.50", "10", "$5.00"],
    ]
    for i, row in enumerate(grid_text):
        for j, cell in enumerate(row):
            page6.insert_text((100 + j * 100, 100 + i * 50), cell)

    # Add metadata with creation and modification dates
    doc.set_metadata(
        {
            "title": "Test PDF",
            "author": "Pytest",
            "subject": "Testing",
            "keywords": "test,pdf,processing",
            "creationDate": "D:20240113205000",
            "modDate": "D:20240113205000",
        }
    )

    doc.save(test_file)
    doc.close()

    yield test_file

    # Cleanup
    if test_file.exists():
        test_file.unlink()


def draw_table(page, table_data, top, left, col_width, row_height):
    """Helper function to draw tables in PDF."""
    for i, row in enumerate(table_data):
        for j, cell in enumerate(row):
            x = left + j * col_width
            y = top + i * row_height
            page.draw_rect(pymupdf.Rect(x, y, x + col_width, y + row_height))
            page.insert_text((x + 5, y + 10), cell)


@pytest.fixture(scope="function")
def pdf_processor():
    """Fixture to create an instance of PdfProcessor."""
    with multiprocessing.Manager() as manager:
        return PdfProcessor(manager)


@pytest.fixture(scope="module")
def ibm_annual_report_path():
    return "/Users/mg/Downloads/IBM_Annual_Report_2022.pdf"


def test_pdf_processor_initialization(pdf_processor):
    """Test initialization of PdfProcessor."""
    assert pdf_processor is not None
    assert isinstance(pdf_processor.saved_image_hashes, set)


def test_pdf_text_extraction(pdf_processor, complex_test_pdf_path):
    """Test text extraction from a complex PDF file."""
    with pymupdf.open(str(complex_test_pdf_path)) as doc:
        # Test Page 1
        page1_content = pdf_processor.extract_text_from_page(doc[0])
        assert any("This is a test document." in block["content"] for block in page1_content if block["type"] == "text")
        assert any("Heading 1" in block["content"] for block in page1_content if block["type"] == "text")
        assert any(
            "This is some content under heading 1." in block["content"]
            for block in page1_content
            if block["type"] == "text"
        )

        # Test Page 2
        page2_content = pdf_processor.extract_text_from_page(doc[1])
        assert any("Table 1" in block["content"] for block in page2_content if block["type"] == "text")

        # Verify all table headers are present
        headers = ["Header 1", "Header 2", "Header 3"]
        for header in headers:
            assert any(header in block["content"] for block in page2_content if block["type"] == "text")

        # Verify table content
        table_content = ["Row 1, Col 1", "Row 1, Col 2", "Row 1, Col 3", "Row 2, Col 1", "Row 2, Col 2", "Row 2, Col 3"]
        for content in table_content:
            assert any(content in block["content"] for block in page2_content if block["type"] == "text")


def test_pdf_table_extraction_methods(pdf_processor, complex_test_pdf_path):
    """Test different table extraction methods."""
    with pymupdf.open(str(complex_test_pdf_path)) as doc:
        # Test built-in PyMuPDF table extraction
        page2 = doc[1]  # Simple table
        tables = pdf_processor.extract_tables_from_page(page2)
        assert len(tables) > 0, "Built-in table extraction failed"
        assert len(tables[0]) == 3, "Table should have 3 rows"
        assert len(tables[0][0]) == 3, "Table should have 3 columns"

        # Test text block analysis method
        page5 = doc[4]  # Complex table
        tables = pdf_processor.extract_tables_from_page(page5)
        assert len(tables) > 0, "Text block table extraction failed"
        assert any("Widget" in row[0] for row in tables[0]), "Product column not found"
        assert any("Sales" in cell for row in tables[0] for cell in row), "Sales columns not found"

        # Test grid analysis method
        page6 = doc[5]  # Grid-like layout
        tables = pdf_processor.extract_tables_from_page(page6)
        assert len(tables) > 0, "Grid analysis table extraction failed"
        assert any("Item" in row[0] for row in tables[0]), "Header row not found"
        assert any("Price" in row[1] for row in tables[0]), "Price column not found"


def test_table_validation(pdf_processor):
    """Test the _is_likely_table helper method."""
    # Valid table
    valid_table = [["Header 1", "Header 2", "Header 3"], ["Data 1", "Data 2", "Data 3"], ["Data 4", "Data 5", "Data 6"]]
    assert pdf_processor._is_likely_table(valid_table)

    # Invalid cases
    assert not pdf_processor._is_likely_table([]), "Empty table should be invalid"
    assert not pdf_processor._is_likely_table([["Single"]]), "Single cell should be invalid"
    assert not pdf_processor._is_likely_table([["Col1"], ["Col2", "Extra"]]), "Inconsistent columns should be invalid"

    # Sparse table
    sparse_table = [["", ""], ["", ""], ["Data", ""]]
    assert not pdf_processor._is_likely_table(sparse_table), "Too sparse table should be invalid"

    # Minimum valid table
    min_table = [["H1", "H2"], ["D1", "D2"]]
    assert pdf_processor._is_likely_table(min_table), "Minimum valid table should be accepted"


def test_document_chunk_creation(pdf_processor):
    """Test document chunk creation and metadata."""
    # Test chunk creation with text
    chunk_text = "Test chunk content"
    chunk_embedding = [0.1, 0.2, 0.3]  # Simplified embedding
    metadata = {
        "page_number": 1,
        "source": Source.PDF,
        "chunk_number": 1,
        "start_index": 0,
        "end_index": len(chunk_text),
    }
    document_id = "test_doc_123"

    chunk = pdf_processor.create_document_chunk(chunk_text, chunk_embedding, metadata, document_id)

    assert isinstance(chunk, DocumentChunk)
    assert chunk.text == chunk_text
    assert chunk.embeddings == chunk_embedding
    assert chunk.document_id == document_id
    assert isinstance(chunk.metadata, DocumentChunkMetadata)
    assert chunk.metadata.page_number == 1
    assert chunk.metadata.source == Source.PDF
    assert chunk.metadata.chunk_number == 1


@pytest.mark.asyncio
async def test_metadata_inheritance(pdf_processor, complex_test_pdf_path):
    """Test metadata inheritance and processing."""
    processed_docs = []
    async for doc in pdf_processor.process(str(complex_test_pdf_path), "test_id"):
        processed_docs.append(doc)

    assert len(processed_docs) > 0
    doc = processed_docs[0]

    # Check base metadata inheritance
    assert doc.metadata.document_name == os.path.basename(str(complex_test_pdf_path))
    assert doc.metadata.title == "Test PDF"
    assert doc.metadata.author == "Pytest"

    # Check date parsing
    assert isinstance(doc.metadata.creation_date, datetime)
    assert isinstance(doc.metadata.mod_date, datetime)

    # Check chunk metadata inheritance
    for chunk in doc.chunks:
        assert chunk.document_id == "test_id"
        assert isinstance(chunk.metadata, DocumentChunkMetadata)
        assert chunk.metadata.source == Source.PDF


@pytest.mark.asyncio
async def test_error_handling_scenarios(pdf_processor):
    """Test various error handling scenarios."""
    # Test nonexistent file
    with pytest.raises(DocumentProcessingError):
        async for _ in pdf_processor.process("/tmp/nonexistent.pdf", "test_id"):
            pass

    # Test invalid PDF file
    invalid_pdf = "/tmp/invalid.pdf"
    with open(invalid_pdf, "w") as f:
        f.write("Not a PDF file")

    with pytest.raises(DocumentProcessingError):
        async for _ in pdf_processor.process(invalid_pdf, "test_id"):
            pass

    # Test malformed metadata
    malformed_pdf = "/tmp/malformed.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((100, 100), "Test")
    doc.set_metadata({"creationDate": "invalid_date", "modDate": "also_invalid"})
    doc.save(malformed_pdf)
    doc.close()

    # Should handle malformed dates gracefully
    processed = False
    async for doc in pdf_processor.process(malformed_pdf, "test_id"):
        processed = True
        assert doc.metadata.creation_date is not None
        assert doc.metadata.mod_date is not None

    assert processed, "Document with malformed metadata should still be processed"

    # Cleanup
    for file in [invalid_pdf, malformed_pdf]:
        if os.path.exists(file):
            os.remove(file)


@pytest.mark.asyncio
async def test_concurrent_processing(pdf_processor, complex_test_pdf_path):
    """Test concurrent processing of PDF pages."""
    processed_docs = []
    async for doc in pdf_processor.process(str(complex_test_pdf_path), "test_id"):
        processed_docs.append(doc)

    assert len(processed_docs) > 0, "No documents processed"

    # Verify all pages were processed
    processed_pages = set()
    for doc in processed_docs:
        for chunk in doc.chunks:
            if hasattr(chunk.metadata, "page_number"):
                processed_pages.add(chunk.metadata.page_number)

    assert len(processed_pages) == 6, "Not all pages were processed"

    # Verify chunk ordering
    for doc in processed_docs:
        chunk_numbers = [chunk.metadata.chunk_number for chunk in doc.chunks]
        assert chunk_numbers == sorted(chunk_numbers), "Chunks not in correct order"

        # Verify chunk metadata consistency
        page_chunks = {}
        for chunk in doc.chunks:
            page = chunk.metadata.page_number
            if page not in page_chunks:
                page_chunks[page] = []
            page_chunks[page].append(chunk.metadata.chunk_number)

        # Verify chunk numbers are sequential within each page
        for page_nums in page_chunks.values():
            assert page_nums == list(
                range(min(page_nums), max(page_nums) + 1)
            ), "Chunk numbers should be sequential within each page"


def test_pdf_processing_ibm_annual_report(pdf_processor, ibm_annual_report_path):
    """Test processing of IBM annual report."""
    start_time = time.time()

    processed_docs = []
    for doc in pdf_processor.process(str(ibm_annual_report_path), "test_id"):
        processed_docs.append(doc)

    end_time = time.time()
    processing_time = end_time - start_time

    print(f"\nProcessing time: {processing_time:.2f} seconds")
    assert len(processed_docs) > 0, "No documents were processed"

    # Analyze content types
    content_types = Counter(
        chunk.metadata.content_type
        for doc in processed_docs
        for chunk in doc.chunks
        if hasattr(chunk.metadata, "content_type")
    )
    print("\nContent type distribution:")
    for content_type, count in content_types.items():
        print(f"  {content_type}: {count}")

    # Verify metadata
    for doc in processed_docs:
        assert doc.metadata is not None
        if doc.metadata.title:
            assert "IBM" in doc.metadata.title
        assert doc.metadata.total_pages > 100

    # Verify key content is extracted
    all_text = " ".join(chunk.text for doc in processed_docs for chunk in doc.chunks)
    assert "Arvind Krishna" in all_text, "CEO's name not found"
    assert "hybrid cloud" in all_text.lower(), "Key term not found"


if __name__ == "__main__":
    pytest.main([__file__])
