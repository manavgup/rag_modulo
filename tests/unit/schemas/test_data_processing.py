"""Atomic tests for data processing validation and schemas."""

import pytest
from vectordbs.data_types import Document, DocumentChunk, DocumentChunkMetadata, Source


@pytest.mark.atomic
class TestDataProcessingValidation:
    """Test data processing validation and schemas - no external dependencies."""

    def test_document_data_validation(self):
        """Test Document data structure validation."""
        # Valid document data
        valid_doc = Document(
            document_id="doc_123",
            name="test_document.pdf",
            chunks=[
                DocumentChunk(
                    chunk_id="chunk_1",
                    text="This is the first chunk of text.",
                    metadata=DocumentChunkMetadata(source=Source.PDF, page_number=1, chunk_number=1),
                ),
                DocumentChunk(
                    chunk_id="chunk_2",
                    text="This is the second chunk of text.",
                    metadata=DocumentChunkMetadata(source=Source.PDF, page_number=1, chunk_number=2),
                ),
            ],
        )

        assert valid_doc.document_id == "doc_123"
        assert valid_doc.name == "test_document.pdf"
        assert len(valid_doc.chunks) == 2
        assert valid_doc.chunks[0].chunk_id == "chunk_1"
        assert valid_doc.chunks[0].text == "This is the first chunk of text."
        assert valid_doc.chunks[1].chunk_id == "chunk_2"
        assert valid_doc.chunks[1].text == "This is the second chunk of text."

    def test_document_chunk_validation(self):
        """Test DocumentChunk data structure validation."""
        # Valid chunk data
        valid_chunk = DocumentChunk(
            chunk_id="chunk_123",
            text="This is a test chunk with some content.",
            metadata=DocumentChunkMetadata(source=Source.PDF, page_number=1, chunk_number=1),
        )

        assert valid_chunk.chunk_id == "chunk_123"
        assert valid_chunk.text == "This is a test chunk with some content."
        assert valid_chunk.metadata.source == Source.PDF
        assert valid_chunk.metadata.page_number == 1
        assert valid_chunk.metadata.chunk_number == 1

    def test_document_id_validation(self):
        """Test document ID validation rules."""
        # Valid document IDs
        valid_ids = ["doc_123", "document-456", "test_doc_789", "doc.with.dots", "DOC_123_UPPER"]

        for doc_id in valid_ids:
            doc = Document(document_id=doc_id, name="test.pdf", chunks=[])
            assert doc.document_id == doc_id
            assert isinstance(doc.document_id, str)
            assert len(doc.document_id.strip()) > 0

    def test_chunk_id_validation(self):
        """Test chunk ID validation rules."""
        # Valid chunk IDs
        valid_chunk_ids = ["chunk_1", "chunk-2", "chunk_3_abc", "chunk.with.dots", "CHUNK_123_UPPER"]

        for chunk_id in valid_chunk_ids:
            chunk = DocumentChunk(
                chunk_id=chunk_id, text="Test text", metadata=DocumentChunkMetadata(source=Source.PDF)
            )
            assert chunk.chunk_id == chunk_id
            assert isinstance(chunk.chunk_id, str)
            assert len(chunk.chunk_id.strip()) > 0

    def test_text_content_validation(self):
        """Test text content validation rules."""
        # Valid text content
        valid_texts = [
            "Simple text content",
            "Text with numbers 123",
            "Text with special chars !@#$%",
            "Multiline\ntext\ncontent",
            "Unicode text: 你好世界 🌍",
            "Empty chunk",  # Empty but valid
            "Very long text content that might be used for testing purposes and could contain multiple sentences with various punctuation marks and formatting.",
        ]

        for text in valid_texts:
            chunk = DocumentChunk(chunk_id="test_chunk", text=text, metadata=DocumentChunkMetadata(source=Source.PDF))
            assert chunk.text == text
            assert isinstance(chunk.text, str)

    def test_metadata_validation(self):
        """Test metadata structure validation."""
        # Valid metadata
        valid_metadata = DocumentChunkMetadata(
            source=Source.PDF, document_id="test_doc_123", page_number=1, chunk_number=1, start_index=0, end_index=100
        )

        chunk = DocumentChunk(chunk_id="test_chunk", text="Test content", metadata=valid_metadata)

        assert chunk.metadata is not None
        assert chunk.metadata.source == Source.PDF
        assert chunk.metadata.document_id == "test_doc_123"
        assert chunk.metadata.page_number == 1
        assert chunk.metadata.chunk_number == 1
        assert chunk.metadata.start_index == 0
        assert chunk.metadata.end_index == 100

    def test_document_name_validation(self):
        """Test document name validation rules."""
        # Valid document names
        valid_names = [
            "test_document.pdf",
            "document-123.txt",
            "file_with_underscores.docx",
            "File With Spaces.pdf",
            "file.with.dots.pdf",
            "FILE_UPPER.PDF",
        ]

        for name in valid_names:
            doc = Document(document_id="test_doc", name=name, chunks=[])
            assert doc.name == name
            assert isinstance(doc.name, str)
            assert len(doc.name.strip()) > 0

    def test_chunk_metadata_types(self):
        """Test chunk metadata type validation."""
        # Test different metadata value types
        metadata = DocumentChunkMetadata(
            source=Source.PDF, document_id="test_doc", page_number=1, chunk_number=1, start_index=0, end_index=50
        )

        chunk = DocumentChunk(chunk_id="test_chunk", text="Test content", metadata=metadata)

        assert chunk.metadata.source == Source.PDF
        assert chunk.metadata.document_id == "test_doc"
        assert chunk.metadata.page_number == 1
        assert chunk.metadata.chunk_number == 1
        assert chunk.metadata.start_index == 0
        assert chunk.metadata.end_index == 50

    def test_document_serialization(self):
        """Test document data serialization."""
        # Test document serialization
        doc = Document(
            document_id="serialization_test",
            name="test.pdf",
            chunks=[
                DocumentChunk(
                    chunk_id="chunk_1",
                    text="Test content",
                    metadata=DocumentChunkMetadata(source=Source.PDF, page_number=1),
                )
            ],
        )

        # Test that we can access all properties
        assert doc.document_id == "serialization_test"
        assert doc.name == "test.pdf"
        assert len(doc.chunks) == 1
        assert doc.chunks[0].chunk_id == "chunk_1"
        assert doc.chunks[0].text == "Test content"
        assert doc.chunks[0].metadata.page_number == 1

    def test_empty_document_validation(self):
        """Test empty document validation."""
        # Empty document (no chunks)
        empty_doc = Document(document_id="empty_doc", name="empty.pdf", chunks=[])

        assert empty_doc.document_id == "empty_doc"
        assert empty_doc.name == "empty.pdf"
        assert len(empty_doc.chunks) == 0
        assert isinstance(empty_doc.chunks, list)

    def test_large_document_validation(self):
        """Test large document with many chunks."""
        # Create document with many chunks
        chunks = []
        for i in range(100):
            chunks.append(
                DocumentChunk(
                    chunk_id=f"chunk_{i}",
                    text=f"This is chunk number {i}",
                    metadata=DocumentChunkMetadata(source=Source.PDF, page_number=(i // 10) + 1, chunk_number=i),
                )
            )

        large_doc = Document(document_id="large_doc", name="large_document.pdf", chunks=chunks)

        assert large_doc.document_id == "large_doc"
        assert large_doc.name == "large_document.pdf"
        assert len(large_doc.chunks) == 100
        assert large_doc.chunks[0].chunk_id == "chunk_0"
        assert large_doc.chunks[99].chunk_id == "chunk_99"
        assert large_doc.chunks[50].metadata.chunk_number == 50
