from unittest.mock import patch

import numpy as np
import pytest

from rag_solution.data_ingestion.chunking import (
    calculate_cosine_distances,
    combine_sentences,
    get_chunking_method,
    semantic_chunker,
    semantic_chunking,
    simple_chunker,
    simple_chunking,
    split_sentences,
    token_based_chunking,
)


def test_split_sentences() -> None:
    """Test sentence splitting functionality."""
    # Test basic sentence splitting
    text = "This is sentence one. This is sentence two! This is sentence three?"
    sentences = split_sentences(text)
    assert len(sentences) == 3
    assert sentences[0] == "This is sentence one"
    assert sentences[1] == "This is sentence two"
    assert sentences[2] == "This is sentence three"

    # Test empty text
    assert split_sentences("") == [""]

    # Test single sentence
    assert split_sentences("Single sentence.") == ["Single sentence"]

    # Test multiple punctuation
    text = "What?! No way! Yes... Really."
    sentences = split_sentences(text)
    assert len(sentences) == 4

    # Test preservation of internal punctuation
    text = "Mr. Smith went to Washington, D.C. Then he went home."
    sentences = split_sentences(text)
    assert len(sentences) == 2
    assert "Mr. Smith went to Washington, D.C" in sentences[0]


def test_combine_sentences() -> None:
    """Test sentence combination with context."""
    sentences = ["First sentence.", "Second sentence.", "Third sentence."]
    combined = combine_sentences(sentences)

    assert len(combined) == 3
    # First sentence should include the next sentence
    assert "First sentence" in combined[0] and "Second sentence" in combined[0]
    # Middle sentence should include both previous and next
    assert all(s in combined[1] for s in ["First sentence", "Second sentence", "Third sentence"])
    # Last sentence should include the previous sentence
    assert "Second sentence" in combined[2] and "Third sentence" in combined[2]

    # Test single sentence
    single = ["Only sentence."]
    assert combine_sentences(single) == single

    # Test empty list
    assert combine_sentences([]) == []


def test_simple_chunking() -> None:
    """Test simple text chunking with overlap."""
    text = "This is a test text that needs to be chunked into smaller pieces for processing."

    # Test basic chunking
    chunks = simple_chunking(text, min_chunk_size=10, max_chunk_size=20, overlap=5)
    assert all(len(chunk) >= 10 for chunk in chunks)
    assert all(len(chunk) <= 20 for chunk in chunks[:-1])  # Last chunk might be smaller

    # Test empty text
    assert simple_chunking("", min_chunk_size=10, max_chunk_size=20, overlap=5) == []

    # Test text smaller than min_chunk_size
    small_text = "Small"
    chunks = simple_chunking(small_text, min_chunk_size=10, max_chunk_size=20, overlap=5)
    assert len(chunks) == 1
    assert chunks[0] == small_text

    # Test invalid parameters
    with pytest.raises(ValueError):
        simple_chunking(text, min_chunk_size=20, max_chunk_size=10, overlap=5)

    # Test no overlap
    chunks = simple_chunking(text, min_chunk_size=10, max_chunk_size=20, overlap=0)
    assert len(chunks) > 1

    # Test full overlap
    chunks = simple_chunking(text, min_chunk_size=10, max_chunk_size=20, overlap=19)
    assert len(chunks) > len(text) // 20  # Should have more chunks due to high overlap


def test_semantic_chunking() -> None:
    """Test semantic-based text chunking."""
    text = "This is the first topic. This is also about the first topic. " "This is a new topic. This is also about the new topic. " "This is a third topic. This is also about the third topic."

    # Mock embeddings for testing
    mock_embeddings = np.array(
        [
            [1.0, 0.0, 0.0],  # First topic embeddings
            [0.9, 0.1, 0.0],
            [0.0, 1.0, 0.0],  # Second topic embeddings
            [0.1, 0.9, 0.0],
            [0.0, 0.0, 1.0],  # Third topic embeddings
            [0.0, 0.1, 0.9],
        ]
    )

    with patch("rag_solution.data_ingestion.chunking.get_embeddings", return_value=mock_embeddings):
        chunks = semantic_chunking(text)
        assert len(chunks) > 1  # Should identify multiple semantic chunks

        # Test empty text
        assert semantic_chunking("") == []

        # Test single sentence
        single = "This is a single sentence about one topic."
        chunks = semantic_chunking(single)
        assert len(chunks) == 1
        assert chunks[0] == single


def test_token_based_chunking() -> None:
    """Test token-aware text chunking."""
    text = "This is a test text. It has multiple sentences. " "We want to ensure proper tokenization. And respect max tokens."

    # Mock tokenization
    mock_tokens = [[1, 2, 3, 4], [1, 2, 3], [1, 2, 3, 4, 5], [1, 2, 3]]

    with patch("rag_solution.data_ingestion.chunking.get_tokenization", return_value=mock_tokens):
        chunks = token_based_chunking(text, max_tokens=10, overlap=2)
        assert len(chunks) > 1

        # Test empty text
        assert token_based_chunking("") == []

        # Test text with fewer tokens than max
        short_text = "Short text."
        with patch("rag_solution.data_ingestion.chunking.get_tokenization", return_value=[[1, 2]]):
            chunks = token_based_chunking(short_text, max_tokens=10, overlap=2)
            assert len(chunks) == 1
            assert chunks[0] == short_text


def test_calculate_cosine_distances() -> None:
    """Test cosine distance calculation."""
    # Test with simple 2D embeddings
    embeddings = np.array([[1.0, 0.0], [1.0, 0.0], [0.0, 1.0], [0.0, 1.0]])

    distances = calculate_cosine_distances(embeddings)
    assert len(distances) == len(embeddings) - 1
    assert distances[0] == 0.0  # First two vectors are identical
    assert distances[1] > 0.0  # Different vectors should have non-zero distance
    assert distances[2] == 0.0  # Last two vectors are identical

    # Test with single embedding
    single_embedding = np.array([[1.0, 0.0]])
    assert calculate_cosine_distances(single_embedding) == []

    # Test with empty embeddings
    assert calculate_cosine_distances(np.array([])) == []


def test_get_chunking_method() -> None:
    """Test chunking method factory function."""
    from core.config import get_settings
    settings = get_settings()

    # Test semantic chunking selection
    with patch.object(settings, "chunking_strategy", "semantic"):
        chunker = get_chunking_method()
        assert chunker == semantic_chunker

    # Test simple chunking selection
    with patch.object(settings, "chunking_strategy", "simple"):
        chunker = get_chunking_method()
        assert chunker == simple_chunker

    # Test default fallback
    with patch.object(settings, "chunking_strategy", "unknown"):
        chunker = get_chunking_method()
        assert chunker == simple_chunker


def test_chunker_integration() -> None:
    """Test integration of chunking methods with settings."""
    from core.config import get_settings
    settings = get_settings()

    text = "This is a test text. It should be chunked according to settings."

    # Test simple chunker with settings
    with (
        patch.object(settings, "min_chunk_size", 10),
        patch.object(settings, "max_chunk_size", 50),
        patch.object(settings, "chunk_overlap", 5),
    ):
        chunks = simple_chunker(text)
        assert len(chunks) > 0
        assert all(len(chunk) >= 10 for chunk in chunks)
        assert all(len(chunk) <= 50 for chunk in chunks[:-1])

    # Test semantic chunker with settings
    mock_embeddings = np.array([[1.0, 0.0], [0.9, 0.1], [0.0, 1.0]])
    with (
        patch("rag_solution.data_ingestion.chunking.get_embeddings", return_value=mock_embeddings),
        patch.object(settings, "min_chunk_size", 10),
        patch.object(settings, "max_chunk_size", 50),
    ):
        chunks = semantic_chunker(text)
        assert len(chunks) > 0
        assert all(len(chunk) >= 10 for chunk in chunks)


def test_edge_cases() -> None:
    """Test edge cases and error handling."""
    # Test handling of special characters
    special_text = "This has\nline breaks. And\ttabs. And    multiple    spaces."
    sentences = split_sentences(special_text)
    assert len(sentences) == 3

    # Test handling of URLs and technical content
    technical_text = "Check https://example.com. Use pip install package."
    sentences = split_sentences(technical_text)
    assert len(sentences) == 2

    # Test handling of quoted text
    quoted_text = 'He said "This is a quote!" and left. She replied "Okay."'
    sentences = split_sentences(quoted_text)
    assert len(sentences) == 2

    # Test handling of lists and bullet points
    list_text = "1. First item. • Second item. * Third item."
    sentences = split_sentences(list_text)
    assert len(sentences) == 3


if __name__ == "__main__":
    pytest.main([__file__])
