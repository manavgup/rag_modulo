import pytest
import asyncio
import os
from rag_solution.data_ingestion.ingestion import ingest_documents
from rag_solution.data_ingestion.pdf_processor import PdfProcessor
from vectordbs.factory import get_datastore
from core.config import settings
from vectordbs.data_types import QueryWithEmbedding, DocumentChunkWithScore

@pytest.mark.asyncio
async def test_pdf_ingestion():
    # Set up the test environment
    test_file_path = os.path.join(os.path.dirname(__file__), 'test_files', 'complex_test.pdf')
    test_collection_name = "test_collection"
    
    # Initialize the vector store
    vector_store = get_datastore(settings.vector_db)
    
    try:
        # Ensure the collection is empty before the test
        vector_store.delete_collection(test_collection_name)
        vector_store.create_collection(test_collection_name)
        
        # Process and ingest the document
        await ingest_documents([test_file_path], vector_store, test_collection_name)
        
     
        # Retrieve and verify the content of the ingested documents
        results = vector_store.retrieve_documents("content", test_collection_name, 5)
        assert len(results) > 0, "No results returned from query"
        
        # Check if the content of the results matches expected content from the PDF
        expected_content = "This is a test document."  # Updated to match actual content
        assert any(expected_content in chunk.text for result in results for chunk in result.data), "Expected content not found in results"
    
    finally:
        # Clean up
        vector_store.delete_collection(test_collection_name)

@pytest.mark.asyncio
async def test_pdf_processor():
    processor = PdfProcessor()
    test_file_path = os.path.join(os.path.dirname(__file__), 'test_files', 'complex_test.pdf')
    
    # Process the document
    documents = [doc async for doc in processor.process(test_file_path)]
    
    # Assert that we got at least one document
    assert len(documents) > 0, "No documents were processed"
    
    # Assert the document has the correct structure
    assert documents[0].name == "complex_test.pdf"
    assert len(documents[0].chunks) > 0, "No chunks were created"
    
    # Check for expected content in the chunks
    expected_content = "This is a test document."  # Update with actual content
    assert any(expected_content in chunk.text for chunk in documents[0].chunks), "Expected content not found in chunks"

    # Print chunk contents for debugging
    for doc in documents:
        for chunk in doc.chunks:
            print(f"Chunk text: {chunk.text}")

if __name__ == "__main__":
    pytest.main()