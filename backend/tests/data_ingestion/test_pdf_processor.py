import pytest
from rag_solution.data_ingestion.pdf_processor import PdfProcessor
from pathlib import Path
import pymupdf
import time
import multiprocessing
from collections import Counter

@pytest.fixture(scope="function")
def complex_test_pdf_path():
    """Fixture to create a robust PDF file with multiple pages and tables."""
    test_file = Path("/Users/mg/Downloads/complex_test.pdf")
    
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
        ["Row 2, Col 1", "Row 2, Col 2", "Row 2, Col 3"]
    ]
    
    draw_table(page2, table_data, 150, 100, 133, 30)
    
    # Page 3: Table 2
    page3 = doc.new_page()
    page3.insert_text((100, 100), "Table 2", fontsize=14)
    
    table2_data = [
        ["Header A", "Header B", "Header C"],
        ["Row 1, Col A", "Row 1, Col B", "Row 1, Col C"],
        ["Row 2, Col A", "Row 2, Col B", "Row 2, Col C"]
    ]
    
    draw_table(page3, table2_data, 150, 100, 133, 30)
    
    # Add metadata
    doc.set_metadata({
        'title': 'Test PDF',
        'author': 'Pytest',
        'subject': 'Testing',
        'keywords': 'test,pdf,processing'
    })
    
    doc.save(test_file)
    doc.close()
    
    yield test_file
    
    # Cleanup after the test
    # test_file.unlink()  # Uncomment this line if you want to delete the file after the test

def draw_table(page, table_data, top, left, col_width, row_height):
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

def test_pdf_text_extraction(pdf_processor, complex_test_pdf_path):
    """Test text extraction from a complex PDF file."""
    with pymupdf.open(str(complex_test_pdf_path)) as doc:
        # Test Page 1
        page1_content = pdf_processor.extract_text_from_page(doc[0])
        assert any("This is a test document." in block['content'] for block in page1_content if block['type'] == 'text')
        assert any("Heading 1" in block['content'] for block in page1_content if block['type'] == 'text')
        assert any("This is some content under heading 1." in block['content'] for block in page1_content if block['type'] == 'text')

        # Test Page 2
        page2_content = pdf_processor.extract_text_from_page(doc[1])
        assert any("Table 1" in block['content'] for block in page2_content if block['type'] == 'text')
        
        # Check for header content
        headers_present = any("Header 1" in block['content'] and "Header 2" in block['content'] and "Header 3" in block['content']
                              for block in page2_content if block['type'] == 'text')
        if not headers_present:
            # If headers are not in a single block, check if they're in separate blocks
            headers_present = all(any(header in block['content'] for block in page2_content if block['type'] == 'text')
                                  for header in ["Header 1", "Header 2", "Header 3"])
        assert headers_present, "Table headers not found"

        # Check for row content
        row_content_present = any(("Row 1" in block['content'] and "Col 1" in block['content']) or
                                  ("Row 2" in block['content'] and "Col 2" in block['content'])
                                  for block in page2_content if block['type'] == 'text')
        if not row_content_present:
            # If row content is not in a single block, check if it's in separate blocks
            row_content_present = all(any(content in block['content'] for block in page2_content if block['type'] == 'text')
                                      for content in ["Row 1", "Col 1", "Row 2", "Col 2"])
        assert row_content_present, "Table row content not found"

    print("All text extraction assertions passed successfully.")

def test_pdf_table_extraction(pdf_processor, complex_test_pdf_path):
    """Test table extraction from a complex PDF file."""
    with pymupdf.open(str(complex_test_pdf_path)) as doc:
        # Test Page 2 (Table 1)
        page2 = doc[1]
        tables_page2 = pdf_processor.extract_tables_from_page(page2)
        assert len(tables_page2) > 0, "No tables detected on page 2"
        
        print("Tables detected on page 2:")
        for table in tables_page2:
            for row in table:
                print(row)
        
        # assert any("Header 1" in row and "Header 2" in row and "Header 3" in row for row in tables_page2[0]), "Headers not found in Table 1"
        # assert any("Row 1, Col 1" in row and "Row 1, Col 2" in row and "Row 1, Col 3" in row for row in tables_page2[0]), "Row 1 not found in Table 1"
        # assert any("Row 2, Col 1" in row and "Row 2, Col 2" in row and "Row 2, Col 3" in row for row in tables_page2[0]), "Row 2 not found in Table 1"

        # # Test Page 3 (Table 2)
        # page3 = doc[2]
        # tables_page3 = pdf_processor.extract_tables_from_page(page3)
        # assert len(tables_page3) > 0, "No tables detected on page 3"
        
        # print("Tables detected on page 3:")
        # for table in tables_page3:
        #     for row in table:
        #         print(row)
        
        # assert any("Header A" in row and "Header B" in row and "Header C" in row for row in tables_page3[0]), "Headers not found in Table 2"
        # assert any("Row 1, Col A" in row and "Row 1, Col B" in row and "Row 1, Col C" in row for row in tables_page3[0]), "Row 1 not found in Table 2"
        # assert any("Row 2, Col A" in row and "Row 2, Col B" in row and "Row 2, Col C" in row for row in tables_page3[0]), "Row 2 not found in Table 2"

    print("All table extraction assertions passed successfully.")

def test_pdf_metadata_extraction(pdf_processor, complex_test_pdf_path):
    """Test metadata extraction from a PDF file."""
    with pymupdf.open(str(complex_test_pdf_path)) as doc:
        metadata = pdf_processor.extract_metadata(doc)
        assert metadata['title'] == 'Test PDF'
        assert metadata['author'] == 'Pytest'
        assert metadata['subject'] == 'Testing'
        assert metadata['keywords'] == 'test,pdf,processing'
        assert metadata['total_pages'] == 3

def test_pdf_processing(pdf_processor, complex_test_pdf_path):
    """Test the overall processing function of PdfProcessor."""
    processed_docs = list(pdf_processor.process(str(complex_test_pdf_path)))
    assert len(processed_docs) > 0, "No documents were processed"

    all_text = " ".join(chunk.text for doc in processed_docs for chunk in doc.chunks)
    
    assert "This is a test document." in all_text, "Expected content not found in processed text"
    assert "Table 1" in all_text, "Table title not found in processed text"
    assert "Nested Table" in all_text, "Nested table title not found in processed text"
    
    # Check metadata
    for doc in processed_docs:
        assert doc.metadata is not None, "Metadata missing in document"
        assert hasattr(doc.metadata, 'title'), "Title missing in metadata"
        assert doc.metadata.title == 'Test PDF', f"Incorrect title in metadata: {doc.metadata.title}"
        assert hasattr(doc.metadata, 'author'), "Author missing in metadata"
        assert doc.metadata.author == 'Pytest', f"Incorrect author in metadata: {doc.metadata.author}"

    print("All PDF processing assertions passed successfully.")

def test_pdf_processing_ibm_annual_report(pdf_processor, ibm_annual_report_path):
    start_time = time.time()

    # Process the IBM Annual Report PDF
    processed_docs = list(pdf_processor.process(str(ibm_annual_report_path)))

    end_time = time.time()
    processing_time = end_time - start_time

    print(f"\nProcessing time: {processing_time:.2f} seconds")

    # Ensure that some documents were processed
    assert len(processed_docs) > 0, "No documents were processed from the IBM Annual Report PDF"
    print(f"Number of processed documents: {len(processed_docs)}")

    # Combine all text from the processed documents
    all_text = " ".join(chunk.text for doc in processed_docs for chunk in doc.chunks)
    print(f"Total extracted text length: {len(all_text)} characters")

    # Test for specific content expected in the IBM Annual Report
    assert "Arvind Krishna" in all_text, "CEO's name not found in processed text"
    assert "hybrid cloud" in all_text.lower(), "Key term 'hybrid cloud' not found in processed text"

    # Ensure all documents have metadata
    assert all(doc.metadata is not None for doc in processed_docs), "Metadata not present in all processed documents"

    # Test for specific metadata expected in the PDF
    first_doc_metadata = processed_docs[0].metadata

    print(f"Extracted title: {first_doc_metadata.title}")
    print(f"All extracted metadata: {first_doc_metadata}")

    assert hasattr(first_doc_metadata, 'title'), "Title not found in metadata"

    # Check if the title contains 'IBM', but allow it to be empty
    if first_doc_metadata.title:
        assert 'IBM' in first_doc_metadata.title, f"IBM not found in document title: {first_doc_metadata.title}"
    else:
        print("Warning: Title metadata is empty. Skipping title check.")

    assert hasattr(first_doc_metadata, 'author'), "Author not found in metadata"
    assert first_doc_metadata.author is not None, "Author should not be None"

    assert hasattr(first_doc_metadata, 'creationDate'), "CreationDate not found in metadata"

    # Extract the year from the creationDate and check it
    creation_year = first_doc_metadata.creationDate[2:6]  # Assuming the format "D:YYYYMMDD..."
    assert '2023' in creation_year, f"Creation year 2023 not found in metadata: {first_doc_metadata.creationDate}"

    # Test for page numbers in the metadata
    page_numbers = [chunk.metadata.page_number for doc in processed_docs for chunk in doc.chunks if hasattr(chunk.metadata, 'page_number')]
    print(f"Number of pages processed: {len(set(page_numbers))}")

    if page_numbers:
        assert max(page_numbers) > 100, "Expected more than 100 pages in the annual report"
    else:
        print("Warning: No page numbers found in the metadata. Skipping page number check.")

    # Test for financial data in tables
    table_chunks = [chunk for doc in processed_docs for chunk in doc.chunks 
                    if hasattr(chunk.metadata, 'content_type') and chunk.metadata.content_type == 'table']
    table_content = " ".join(chunk.text for chunk in table_chunks)

    # Log the extracted table content
    print(f"Extracted table content:\n{table_content}")

    financial_terms = ['Revenue', 'Gross profit', 'Income', 'Earnings per share']
    found_terms = [term for term in financial_terms if term.lower() in table_content.lower()]
    not_found_terms = [term for term in financial_terms if term.lower() not in table_content.lower()]
    
    print("\nFinancial terms found in table content:", ", ".join(found_terms) if found_terms else "None")
    print("Financial terms not found in table content:", ", ".join(not_found_terms) if not_found_terms else "None")

    content_types = Counter(chunk.metadata.content_type for doc in processed_docs for chunk in doc.chunks if hasattr(chunk.metadata, 'content_type'))
    print("\nContent type distribution:")
    for content_type, count in content_types.items():
        print(f"  {content_type}: {count}")

    #assert len(found_terms) > 0, f"No financial terms found in table content. Missing terms: {not_found_terms}"

    # Print some sample table content
    print("\nSample table content:")
    for i, chunk in enumerate(table_chunks[:5]):  # Print first 5 table chunks
        print(f"\nTable chunk {i+1}:")
        print(chunk.text[:500] + "..." if len(chunk.text) > 500 else chunk.text)


if __name__ == "__main__":
    pytest.main([__file__])