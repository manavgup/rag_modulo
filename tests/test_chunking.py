# tests/test_chunking.py
import pytest

from rag_solution.data_ingestion.chunking import (semantic_chunking,
                                                  semantic_chunking_for_tables,
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
    chunks = semantic_chunking(text, min_chunk_size, max_chunk_size, 0.4)
    assert len(chunks) > 0
    for chunk in chunks:
        print(f"Chunk: {chunk}, Length: {len(chunk)}")
    assert all(len(chunk) <= max_chunk_size for chunk in chunks)


def test_semantic_chunking_for_tables():
    tables = [
        [
            ["Header 1", "Header 2"],
            ["Row 1 Col 1", "Row 1 Col 2"],
            ["Row 2 Col 1", "Row 2 Col 2"],
        ],
        [["Header A", "Header B"], ["Row 1 A", "Row 1 B"], ["Row 2 A", "Row 2 B"]],
    ]
    min_chunk_size = 20
    max_chunk_size = 100
    chunks = semantic_chunking_for_tables(tables, min_chunk_size, max_chunk_size, 0.4)
    print(f"** Chunks: {chunks}")
    assert len(chunks) > 0
    for chunk in chunks:
        print(f"Chunk: {chunk}, Length: {len(chunk)}")
    assert all(len(chunk) <= max_chunk_size for chunk in chunks)
    assert all(len(chunk) >= min_chunk_size for chunk in chunks)
