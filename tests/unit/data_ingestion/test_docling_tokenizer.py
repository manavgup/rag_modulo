"""Unit tests for DoclingProcessor tokenizer configuration.

Tests tokenizer initialization, error handling, and token counting accuracy.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from transformers import PreTrainedTokenizerBase

from backend.core.config import Settings
from backend.rag_solution.data_ingestion.docling_processor import DoclingProcessor


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    settings = Mock(spec=Settings)
    # Chunking settings
    settings.min_chunk_size = 100
    settings.max_chunk_size = 300
    settings.chunk_overlap = 10
    settings.chunking_strategy = "sentence"
    settings.chunking_max_tokens = 400
    settings.chunking_tokenizer_model = "ibm-granite/granite-embedding-english-r2"
    # Other required settings
    settings.semantic_threshold = 0.5
    return settings


@pytest.fixture
def mock_tokenizer():
    """Create mock tokenizer."""
    tokenizer = Mock(spec=PreTrainedTokenizerBase)
    tokenizer.encode = Mock(return_value=[1, 2, 3, 4, 5])  # 5 tokens
    tokenizer.tokenize = Mock(return_value=["tok1", "tok2", "tok3"])  # 3 tokens (should not be used)
    return tokenizer


class TestDoclingProcessorTokenizerInit:
    """Test tokenizer initialization in DoclingProcessor."""

    @patch("backend.rag_solution.data_ingestion.docling_processor.DocumentConverter")
    @patch("backend.rag_solution.data_ingestion.docling_processor.AutoTokenizer")
    @patch("backend.rag_solution.data_ingestion.docling_processor.HybridChunker")
    def test_tokenizer_loads_from_settings(self, mock_chunker_cls, mock_tokenizer_cls, mock_converter_cls, mock_settings, mock_tokenizer):
        """Test that tokenizer is loaded from settings configuration."""
        mock_tokenizer_cls.from_pretrained.return_value = mock_tokenizer
        mock_converter_cls.return_value = Mock()
        mock_chunker_cls.return_value = Mock()

        processor = DoclingProcessor(mock_settings)

        # Verify AutoTokenizer.from_pretrained was called with correct model and revision
        mock_tokenizer_cls.from_pretrained.assert_called_once_with(
            "ibm-granite/granite-embedding-english-r2",
            revision="main",
        )
        assert processor.tokenizer == mock_tokenizer

    @patch("backend.rag_solution.data_ingestion.docling_processor.DocumentConverter")
    @patch("backend.rag_solution.data_ingestion.docling_processor.AutoTokenizer")
    def test_tokenizer_download_failure_raises_value_error(self, mock_tokenizer_cls, mock_converter_cls, mock_settings):
        """Test that tokenizer download failure raises ValueError with helpful message."""
        mock_converter_cls.return_value = Mock()
        mock_tokenizer_cls.from_pretrained.side_effect = Exception("Network error")

        with pytest.raises(ValueError) as exc_info:
            DoclingProcessor(mock_settings)

        error_msg = str(exc_info.value)
        assert "Cannot initialize DoclingProcessor" in error_msg
        assert "ibm-granite/granite-embedding-english-r2" in error_msg
        assert "network connectivity" in error_msg.lower()

    @patch("backend.rag_solution.data_ingestion.docling_processor.DocumentConverter")
    @patch("backend.rag_solution.data_ingestion.docling_processor.AutoTokenizer")
    @patch("backend.rag_solution.data_ingestion.docling_processor.HybridChunker")
    def test_max_tokens_uses_settings_value(self, mock_chunker_cls, mock_tokenizer_cls, mock_converter_cls, mock_settings, mock_tokenizer):
        """Test that max_tokens parameter respects CHUNKING_MAX_TOKENS setting."""
        mock_tokenizer_cls.from_pretrained.return_value = mock_tokenizer
        mock_converter_cls.return_value = Mock()
        mock_chunker = Mock()
        mock_chunker_cls.return_value = mock_chunker

        processor = DoclingProcessor(mock_settings)

        # Verify HybridChunker was initialized with correct max_tokens
        # Should use min(max_chunk_size=300, chunking_max_tokens=400) = 300
        mock_chunker_cls.assert_called_once()
        call_kwargs = mock_chunker_cls.call_args.kwargs
        assert call_kwargs["max_tokens"] == 300

    @patch("backend.rag_solution.data_ingestion.docling_processor.DocumentConverter")
    @patch("backend.rag_solution.data_ingestion.docling_processor.AutoTokenizer")
    @patch("backend.rag_solution.data_ingestion.docling_processor.HybridChunker")
    def test_max_tokens_respects_safety_margin(self, mock_chunker_cls, mock_tokenizer_cls, mock_converter_cls, mock_settings, mock_tokenizer):
        """Test that max_tokens uses chunking_max_tokens when it's the smaller value."""
        mock_tokenizer_cls.from_pretrained.return_value = mock_tokenizer
        mock_converter_cls.return_value = Mock()
        mock_chunker = Mock()
        mock_chunker_cls.return_value = mock_chunker

        # Set max_chunk_size > chunking_max_tokens to test min() logic
        mock_settings.max_chunk_size = 500
        mock_settings.chunking_max_tokens = 400

        processor = DoclingProcessor(mock_settings)

        # Should use chunking_max_tokens (400) as it's smaller
        call_kwargs = mock_chunker_cls.call_args.kwargs
        assert call_kwargs["max_tokens"] == 400


class TestDoclingProcessorTokenCounting:
    """Test token counting accuracy in DoclingProcessor."""

    @pytest.mark.asyncio
    @patch("backend.rag_solution.data_ingestion.docling_processor.DocumentConverter")
    @patch("backend.rag_solution.data_ingestion.docling_processor.AutoTokenizer")
    @patch("backend.rag_solution.data_ingestion.docling_processor.HybridChunker")
    async def test_token_count_uses_encode_with_special_tokens(
        self, mock_chunker_cls, mock_tokenizer_cls, mock_converter_cls, mock_settings, mock_tokenizer
    ):
        """Test that token counting uses encode() with add_special_tokens=True."""
        mock_tokenizer_cls.from_pretrained.return_value = mock_tokenizer
        mock_converter_cls.return_value = Mock()

        # Mock DoclingChunk with metadata
        mock_docling_chunk = Mock()
        mock_docling_chunk.text = "This is a test chunk"
        mock_docling_chunk.meta = Mock()
        mock_docling_chunk.meta.doc_items = []
        mock_docling_chunk.meta.headings = []

        # Mock chunker to return our test chunk
        mock_chunker = Mock()
        mock_chunker.chunk.return_value = [mock_docling_chunk]
        mock_chunker_cls.return_value = mock_chunker

        processor = DoclingProcessor(mock_settings)

        # Mock docling document
        mock_doc = Mock()

        # Process document
        chunks = await processor._convert_to_chunks(mock_doc, "test-doc-id")

        # Verify encode() was called with add_special_tokens=True
        mock_tokenizer.encode.assert_called_once_with("This is a test chunk", add_special_tokens=True)

        # Verify tokenize() was NOT called (old method)
        mock_tokenizer.tokenize.assert_not_called()

    @pytest.mark.asyncio
    @patch("backend.rag_solution.data_ingestion.docling_processor.DocumentConverter")
    @patch("backend.rag_solution.data_ingestion.docling_processor.AutoTokenizer")
    @patch("backend.rag_solution.data_ingestion.docling_processor.HybridChunker")
    async def test_token_count_fallback_on_error(
        self, mock_chunker_cls, mock_tokenizer_cls, mock_converter_cls, mock_settings
    ):
        """Test that token counting falls back to estimation on error."""
        # Create a tokenizer that raises an error on encode
        mock_broken_tokenizer = Mock(spec=PreTrainedTokenizerBase)
        mock_broken_tokenizer.encode.side_effect = RuntimeError("Tokenizer error")

        mock_tokenizer_cls.from_pretrained.return_value = mock_broken_tokenizer
        mock_converter_cls.return_value = Mock()

        # Mock DoclingChunk
        test_text = "A" * 100  # 100 characters
        mock_docling_chunk = Mock()
        mock_docling_chunk.text = test_text
        mock_docling_chunk.meta = Mock()
        mock_docling_chunk.meta.doc_items = []
        mock_docling_chunk.meta.headings = []

        mock_chunker = Mock()
        mock_chunker.chunk.return_value = [mock_docling_chunk]
        mock_chunker_cls.return_value = mock_chunker

        processor = DoclingProcessor(mock_settings)
        mock_doc = Mock()

        # Process document (should not raise, should use fallback)
        chunks = await processor._convert_to_chunks(mock_doc, "test-doc-id")

        # Verify chunk was created (fallback estimation used)
        assert len(chunks) == 1
        # Fallback uses len(text) // 4 = 100 // 4 = 25 tokens


class TestDoclingProcessorTypeHints:
    """Test that proper type hints are used."""

    @patch("backend.rag_solution.data_ingestion.docling_processor.DocumentConverter")
    @patch("backend.rag_solution.data_ingestion.docling_processor.AutoTokenizer")
    @patch("backend.rag_solution.data_ingestion.docling_processor.HybridChunker")
    def test_tokenizer_has_correct_type_hint(self, mock_chunker_cls, mock_tokenizer_cls, mock_converter_cls, mock_settings, mock_tokenizer):
        """Test that tokenizer attribute has PreTrainedTokenizerBase type hint."""
        mock_tokenizer_cls.from_pretrained.return_value = mock_tokenizer
        mock_converter_cls.return_value = Mock()
        mock_chunker_cls.return_value = Mock()

        processor = DoclingProcessor(mock_settings)

        # Verify tokenizer is set and has correct type
        assert processor.tokenizer is not None
        assert isinstance(processor.tokenizer, (Mock, PreTrainedTokenizerBase))

        # Check class annotation (verifies type hint exists)
        annotations = DoclingProcessor.__annotations__
        assert "tokenizer" in annotations
        # Type hint should be PreTrainedTokenizerBase | None
        assert "PreTrainedTokenizerBase" in str(annotations["tokenizer"])
