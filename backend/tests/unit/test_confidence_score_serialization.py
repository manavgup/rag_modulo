"""Test confidence score serialization in QueryResult and SearchOutput."""

import json

import pytest
from pydantic import UUID4

from rag_solution.schemas.search_schema import SearchOutput
from vectordbs.data_types import (
    DocumentChunkMetadata,
    DocumentChunkWithScore,
    DocumentMetadata,
    QueryResult,
    Source,
)


def test_query_result_score_serialization():
    """Test that QueryResult.score is properly serialized to JSON."""
    # Create a QueryResult with a score
    chunk = DocumentChunkWithScore(
        chunk_id="test-chunk-1",
        text="This is a test chunk",
        score=0.85,
        metadata=DocumentChunkMetadata(
            source=Source.PDF,
            document_id="doc-1",
            page_number=1,
            chunk_number=1,
        ),
        document_id="doc-1",
    )

    query_result = QueryResult(chunk=chunk, score=0.85, embeddings=[])

    # Serialize to JSON
    json_data = query_result.model_dump()

    # Verify score is present
    assert json_data["score"] == 0.85, "QueryResult.score should be 0.85"
    assert json_data["chunk"]["score"] == 0.85, "DocumentChunkWithScore.score should be 0.85"


def test_query_result_score_zero():
    """Test that QueryResult with 0.0 score is properly serialized."""
    chunk = DocumentChunkWithScore(
        chunk_id="test-chunk-2",
        text="This is a test chunk with zero score",
        score=0.0,
        metadata=DocumentChunkMetadata(
            source=Source.PDF,
            document_id="doc-2",
            page_number=1,
            chunk_number=1,
        ),
        document_id="doc-2",
    )

    query_result = QueryResult(chunk=chunk, score=0.0, embeddings=[])

    # Serialize to JSON
    json_data = query_result.model_dump()

    # Verify score is present and is 0.0 (not None)
    assert json_data["score"] == 0.0, "QueryResult.score should be 0.0, not None"
    assert json_data["chunk"]["score"] == 0.0, "DocumentChunkWithScore.score should be 0.0, not None"


def test_search_output_score_serialization():
    """Test that SearchOutput properly serializes QueryResult scores."""
    # Create QueryResults with various scores
    chunks = []
    query_results = []
    for i, score in enumerate([0.95, 0.75, 0.50, 0.25]):
        chunk = DocumentChunkWithScore(
            chunk_id=f"chunk-{i}",
            text=f"Test chunk {i}",
            score=score,
            metadata=DocumentChunkMetadata(
                source=Source.PDF,
                document_id="doc-1",
                page_number=1,
                chunk_number=i,
            ),
            document_id="doc-1",
        )
        chunks.append(chunk)
        query_results.append(QueryResult(chunk=chunk, score=score, embeddings=[]))

    # Create SearchOutput
    search_output = SearchOutput(
        answer="Test answer",
        documents=[
            DocumentMetadata(
                document_name="test.pdf",
                total_pages=10,
                total_chunks=100,
            )
        ],
        query_results=query_results,
        rewritten_query="Test query",
        evaluation=None,
        execution_time=1.5,
    )

    # Serialize to JSON
    json_data = search_output.model_dump()

    # Verify all scores are present
    assert len(json_data["query_results"]) == 4, "Should have 4 query results"
    for i, expected_score in enumerate([0.95, 0.75, 0.50, 0.25]):
        result = json_data["query_results"][i]
        assert result["score"] == expected_score, f"Result {i} should have score {expected_score}"
        assert result["chunk"]["score"] == expected_score, f"Result {i} chunk should have score {expected_score}"


def test_search_output_json_string_serialization():
    """Test that SearchOutput can be serialized to JSON string without losing scores."""
    chunk = DocumentChunkWithScore(
        chunk_id="chunk-1",
        text="Test chunk",
        score=0.87,
        metadata=DocumentChunkMetadata(
            source=Source.PDF,
            document_id="doc-1",
            page_number=1,
            chunk_number=1,
        ),
        document_id="doc-1",
    )

    query_result = QueryResult(chunk=chunk, score=0.87, embeddings=[])

    search_output = SearchOutput(
        answer="Test answer",
        documents=[DocumentMetadata(document_name="test.pdf")],
        query_results=[query_result],
        rewritten_query="Test query",
    )

    # Serialize to JSON string (as would happen in FastAPI)
    json_string = search_output.model_dump_json()

    # Parse back
    parsed = json.loads(json_string)

    # Verify score survived the round-trip
    assert parsed["query_results"][0]["score"] == 0.87, "Score should survive JSON serialization"
    assert parsed["query_results"][0]["chunk"]["score"] == 0.87, "Chunk score should survive JSON serialization"


def test_query_result_none_score():
    """Test that QueryResult with None score is properly handled."""
    chunk = DocumentChunkWithScore(
        chunk_id="chunk-none",
        text="Test chunk with no score",
        score=None,
        metadata=DocumentChunkMetadata(
            source=Source.PDF,
            document_id="doc-3",
            page_number=1,
            chunk_number=1,
        ),
        document_id="doc-3",
    )

    query_result = QueryResult(chunk=chunk, score=None, embeddings=[])

    # Serialize to JSON
    json_data = query_result.model_dump()

    # Verify score is None (not 0.0)
    assert json_data["score"] is None, "QueryResult.score should be None"
    assert json_data["chunk"]["score"] is None, "DocumentChunkWithScore.score should be None"
