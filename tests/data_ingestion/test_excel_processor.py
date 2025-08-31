import pytest
import pandas as pd
import os
from unittest.mock import patch
from rag_solution.data_ingestion.excel_processor import ExcelProcessor
from core.custom_exceptions import DocumentProcessingError
from vectordbs.data_types import Document

@pytest.fixture
def excel_processor():
    """Create an ExcelProcessor instance."""
    return ExcelProcessor()

@pytest.fixture
def sample_excel_path():
    """Create a sample Excel file for testing."""
    file_path = "/tmp/test_data.xlsx"
    
    # Create test data
    df1 = pd.DataFrame({
        'Column1': ['Data1', 'Data2', 'Data3'],
        'Column2': [1, 2, 3],
        'Column3': ['A', 'B', 'C']
    })
    
    df2 = pd.DataFrame({
        'Name': ['John', 'Jane', 'Bob'],
        'Age': [25, 30, 35],
        'City': ['New York', 'London', 'Paris']
    })
    
    # Create Excel writer object
    with pd.ExcelWriter(file_path) as writer:
        df1.to_excel(writer, sheet_name='Sheet1', index=False)
        df2.to_excel(writer, sheet_name='Sheet2', index=False)
    
    yield file_path
    
    # Cleanup
    if os.path.exists(file_path):
        os.remove(file_path)

@pytest.mark.asyncio
async def test_process_excel_file(excel_processor, sample_excel_path):
    """Test processing a valid Excel file."""
    documents = []
    async for doc in excel_processor.process(sample_excel_path):
        documents.append(doc)
    
    assert len(documents) > 0
    assert all(isinstance(doc, Document) for doc in documents)
    
    # Check document content
    all_text = " ".join(doc.text for doc in documents)
    assert "Sheet: Sheet1" in all_text
    assert "Sheet: Sheet2" in all_text
    assert "Column1" in all_text
    assert "Name" in all_text
    assert "Data1" in all_text
    assert "John" in all_text

@pytest.mark.asyncio
async def test_process_empty_excel(excel_processor):
    """Test processing an empty Excel file."""
    empty_file = "/tmp/empty.xlsx"
    df = pd.DataFrame()
    df.to_excel(empty_file, index=False)
    
    documents = []
    async for doc in excel_processor.process(empty_file):
        documents.append(doc)
    
    assert len(documents) > 0  # Should still create at least one document
    
    os.remove(empty_file)

@pytest.mark.asyncio
async def test_process_large_excel(excel_processor):
    """Test processing a large Excel file."""
    large_file = "/tmp/large.xlsx"
    
    # Create large dataset
    large_df = pd.DataFrame({
        'Column1': [f'Data{i}' for i in range(1000)],
        'Column2': range(1000),
        'Column3': [f'Value{i}' for i in range(1000)]
    })
    
    large_df.to_excel(large_file, index=False)
    
    documents = []
    async for doc in excel_processor.process(large_file):
        documents.append(doc)
    
    assert len(documents) > 1  # Should create multiple chunks
    
    os.remove(large_file)

@pytest.mark.asyncio
async def test_process_multiple_sheets(excel_processor, sample_excel_path):
    """Test processing Excel file with multiple sheets."""
    documents = []
    async for doc in excel_processor.process(sample_excel_path):
        documents.append(doc)
    
    all_text = " ".join(doc.text for doc in documents)
    
    # Verify both sheets are processed
    assert "Sheet: Sheet1" in all_text
    assert "Sheet: Sheet2" in all_text
    
    # Verify content from both sheets
    assert "Column1" in all_text and "Name" in all_text
    assert "Data1" in all_text and "John" in all_text

@pytest.mark.asyncio
async def test_process_invalid_file(excel_processor):
    """Test processing an invalid file."""
    invalid_file = "/tmp/invalid.xlsx"
    
    # Create an invalid Excel file
    with open(invalid_file, 'w') as f:
        f.write("Not an Excel file")
    
    with pytest.raises(DocumentProcessingError):
        async for _ in excel_processor.process(invalid_file):
            pass
    
    os.remove(invalid_file)

@pytest.mark.asyncio
async def test_process_nonexistent_file(excel_processor):
    """Test processing a nonexistent file."""
    with pytest.raises(DocumentProcessingError):
        async for _ in excel_processor.process("/tmp/nonexistent.xlsx"):
            pass

@pytest.mark.asyncio
async def test_document_metadata(excel_processor, sample_excel_path):
    """Test document metadata in processed output."""
    documents = []
    async for doc in excel_processor.process(sample_excel_path):
        documents.append(doc)
    
    for doc in documents:
        assert isinstance(doc.document_id, str)
        assert doc.name == os.path.basename(sample_excel_path)
        assert isinstance(doc.text, str)

@pytest.mark.asyncio
async def test_chunking_integration(excel_processor, sample_excel_path):
    """Test integration with chunking method."""
    # Mock chunking method to verify it's called with correct data
    mock_chunks = ["Chunk1", "Chunk2"]
    with patch.object(excel_processor, 'chunking_method', return_value=mock_chunks):
        documents = []
        async for doc in excel_processor.process(sample_excel_path):
            documents.append(doc)
        
        assert len(documents) == len(mock_chunks)
        assert all(doc.text in mock_chunks for doc in documents)

@pytest.mark.asyncio
async def test_special_characters(excel_processor):
    """Test handling of special characters in Excel data."""
    special_file = "/tmp/special.xlsx"
    
    # Create test data with special characters
    df = pd.DataFrame({
        'Column1': ['Data with \n newline', 'Data with \t tab', 'Data with 🌟 emoji'],
        'Column2': ['Data with "quotes"', 'Data with \'single quotes\'', 'Data with &<>']
    })
    
    df.to_excel(special_file, index=False)
    
    documents = []
    async for doc in excel_processor.process(special_file):
        documents.append(doc)
    
    all_text = " ".join(doc.text for doc in documents)
    assert 'newline' in all_text
    assert 'tab' in all_text
    assert 'emoji' in all_text
    assert 'quotes' in all_text
    
    os.remove(special_file)

if __name__ == "__main__":
    pytest.main([__file__])
