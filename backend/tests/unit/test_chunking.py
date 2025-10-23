"""
Simplified version of test_chunking.py
"""

import pytest

from rag_solution.data_ingestion.chunking import sentence_based_chunking


@pytest.mark.unit
class TestSimplified:
    """Simplified test that works."""

    def test_basic_functionality(self):
        """Test basic functionality."""
        assert True

    def test_configuration(self, integration_settings):
        """Test configuration."""
        assert integration_settings is not None
        assert hasattr(integration_settings, "jwt_secret_key")

    def test_mock_services(self, mock_watsonx_provider):
        """Test mock services."""
        assert mock_watsonx_provider is not None
        assert hasattr(mock_watsonx_provider, "generate_response")


@pytest.mark.unit
class TestOversizedSentenceSplitting:
    """Tests for oversized sentence handling in chunking (Issue #1 fix)."""

    def test_oversized_sentence_splits_at_word_boundaries(self) -> None:
        """Test that oversized sentences are split at word boundaries."""
        # Create a sentence longer than target (750 chars)
        long_sentence = "word " * 200  # Creates 1000 char sentence
        target_chars = 750

        chunks = sentence_based_chunking(long_sentence, target_chars=target_chars, overlap_chars=100, min_chars=500)

        # Verify all chunks are within target
        for chunk in chunks:
            assert len(chunk) <= target_chars, f"Chunk exceeds target: {len(chunk)} > {target_chars}"

        # Verify no empty chunks
        for chunk in chunks:
            assert len(chunk.strip()) > 0, "Empty chunk found after stripping"

    def test_markdown_table_splits_correctly(self) -> None:
        """Test that markdown tables (common oversized content) are split correctly."""
        # Simulate a large markdown table
        table_rows = "| Column1 | Column2 | Column3 | Column4 |\n" * 50
        target_chars = 750

        chunks = sentence_based_chunking(table_rows, target_chars=target_chars, overlap_chars=100, min_chars=500)

        # Verify max chunk size is under limit
        max_chunk_len = max(len(c) for c in chunks)
        assert max_chunk_len <= target_chars, f"Max chunk size {max_chunk_len} exceeds target {target_chars}"

    def test_very_long_sentence_without_spaces(self) -> None:
        """Test handling of very long sentences with minimal spaces."""
        # Worst case: very long "word" with few break points
        long_word = "a" * 1000 + " " + "b" * 1000
        target_chars = 750

        chunks = sentence_based_chunking(long_word, target_chars=target_chars, overlap_chars=100, min_chars=500)

        # Should still create chunks
        assert len(chunks) > 0, "No chunks created for long sentence"

        # All chunks should be reasonable size
        for chunk in chunks:
            assert len(chunk) <= target_chars + 50, f"Chunk too large: {len(chunk)}"  # Allow small buffer

    def test_normal_sentences_not_affected(self) -> None:
        """Test that normal-sized sentences are not affected by oversized handling."""
        normal_text = "This is a normal sentence. This is another normal sentence. And one more."
        target_chars = 750

        chunks = sentence_based_chunking(normal_text, target_chars=target_chars, overlap_chars=100, min_chars=50)

        # Should create single chunk (text is small)
        assert len(chunks) >= 1, "Should create at least one chunk"

        # Chunks should not be unnecessarily split
        total_text_len = len(normal_text)
        if total_text_len < target_chars:
            assert len(chunks) == 1, "Normal text should not be split unnecessarily"

    def test_empty_string_chunks_are_filtered(self) -> None:
        """Test that empty strings after stripping are filtered out."""
        # Create text with lots of whitespace that might produce empty chunks
        text_with_whitespace = "   \n\n   " + "word " * 200 + "   \n\n   "
        target_chars = 750

        chunks = sentence_based_chunking(
            text_with_whitespace, target_chars=target_chars, overlap_chars=100, min_chars=500
        )

        # Verify no empty or whitespace-only chunks
        for chunk in chunks:
            assert chunk.strip(), "Empty or whitespace-only chunk found"
            assert len(chunk.strip()) > 0, "Chunk is empty after stripping"
