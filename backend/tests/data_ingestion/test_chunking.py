# tests/test_chunking.py
import pytest
from rag_solution.data_ingestion.chunking import (semantic_chunking,
                                                          simple_chunking)

def test_simple_chunking():
    text = "This is a sample text to test simple chunking."
    min_chunk_size = 10
    max_chunk_size = 50
    overlap = 5
    chunks = simple_chunking(text, min_chunk_size, max_chunk_size, overlap)
    assert len(chunks) > 0
    assert all(len(chunk) <= max_chunk_size for chunk in chunks)

def test_semantic_chunking():
    text = "This is a sample text. It contains multiple sentences. This is for testing."
    min_chunk_size = 20
    max_chunk_size = 100
    chunks = semantic_chunking(text, min_chunk_size, max_chunk_size)
    assert len(chunks) > 0
    for chunk in chunks:
        print(f"Chunk: {chunk}, Length: {len(chunk)}")
    assert all(len(chunk) <= max_chunk_size for chunk in chunks)

def test_simple_chunking_edge_cases():
    # Test with empty text
    assert simple_chunking("", 10, 100, 5) == []
    
    # Test with text shorter than min_chunk_size
    short_text = "Short."
    assert simple_chunking(short_text, 10, 100, 5) == [short_text]
    
    # Test with max_chunk_size smaller than min_chunk_size
    with pytest.raises(ValueError):
        simple_chunking("Any text", 100, 50, 5)

def test_semantic_chunking_edge_cases():
    # Test with empty text
    assert semantic_chunking("", 10, 100) == []
    
    # Test with text shorter than min_chunk_size
    short_text = "Short."
    assert semantic_chunking(short_text, 10, 100) == [short_text]
    
    # Test with max_chunk_size smaller than min_chunk_size
    with pytest.raises(ValueError):
        semantic_chunking("Any text", 100, 50)

# Commented out performance tests as they may not be suitable for all environments
# import time
# def test_chunking_performance():
#     very_large_text = "This is a sample sentence. " * 100000  # Creates a ~2MB text
#     start_time = time.time()
#     chunks = simple_chunking(very_large_text, 100, 1000, 50)
#     end_time = time.time()
#     assert end_time - start_time < 5  # Assumes it should process in less than 5 seconds

#     start_time = time.time()
#     chunks = semantic_chunking(very_large_text, 100, 1000)
#     end_time = time.time()
#     assert end_time - start_time < 30  # Allows more time for semantic processing
