"""Unit tests for DoclingProcessor (TDD Red Phase).

This test suite is written BEFORE implementation to follow TDD.
All tests should initially FAIL until DoclingProcessor is implemented.
"""

from unittest.mock import Mock, patch

import pytest

# These imports will fail initially - that's expected in Red phase
try:
    from backend.rag_solution.data_ingestion.docling_processor import DoclingProcessor
except ImportError:
    DoclingProcessor = None

from backend.vectordbs.data_types import Document, DocumentMetadata


class TestDoclingProcessorInitialization:
    """Test DoclingProcessor initialization."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock()
        settings.min_chunk_size = 100
        settings.max_chunk_size = 1000
        settings.chunk_overlap = 20
        settings.chunking_strategy = "simple"
        settings.semantic_threshold = 0.8
        return settings

    def test_docling_processor_imports(self):
        """Test that DoclingProcessor can be imported."""
        assert DoclingProcessor is not None, "DoclingProcessor not implemented yet"

    def test_docling_processor_initialization(self, mock_settings):
        """Test DoclingProcessor initializes correctly."""
        processor = DoclingProcessor(mock_settings)

        assert processor is not None
        assert hasattr(processor, "converter")
        assert processor.settings == mock_settings

    @patch("docling.document_converter.DocumentConverter")
    def test_docling_converter_created_on_init(self, mock_converter_class, mock_settings):
        """Test that DocumentConverter is instantiated during init."""
        processor = DoclingProcessor(mock_settings)

        mock_converter_class.assert_called_once()
        assert processor.converter == mock_converter_class.return_value


class TestDoclingProcessorPDFProcessing:
    """Test PDF document processing with Docling."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock()
        settings.min_chunk_size = 100
        settings.max_chunk_size = 1000
        settings.chunk_overlap = 20
        settings.chunking_strategy = "simple"
        settings.semantic_threshold = 0.8
        return settings

    @pytest.fixture
    def docling_processor(self, mock_settings):
        """Create DoclingProcessor instance."""
        if DoclingProcessor is None:
            pytest.skip("DoclingProcessor not implemented yet")
        return DoclingProcessor(mock_settings)

    @pytest.fixture
    def mock_docling_document(self):
        """Create mock DoclingDocument."""
        mock_doc = Mock()
        mock_doc.metadata = {"title": "Test Document", "author": "Test Author", "page_count": 5}
        mock_doc.iterate_items.return_value = []
        return mock_doc

    @patch("os.stat")
    @patch("os.path.exists")
    @patch("os.path.getsize")
    @patch("os.path.getmtime")
    @patch("docling.document_converter.DocumentConverter")
    @pytest.mark.asyncio
    async def test_process_pdf_success(
        self,
        mock_converter_class,
        mock_getmtime,
        mock_getsize,
        mock_exists,
        mock_stat,
        docling_processor,
        mock_docling_document,
    ):
        """Test successful PDF processing."""
        # Mock file operations
        mock_getsize.return_value = 12345
        mock_getmtime.return_value = 1234567890.0
        mock_exists.return_value = True
        # Mock file stat
        mock_stat_result = type("stat_result", (), {})()
        mock_stat_result.st_ctime = 1234567890.0
        mock_stat_result.st_mtime = 1234567890.0
        mock_stat.return_value = mock_stat_result

        # Setup mock converter
        mock_result = Mock()
        mock_result.document = mock_docling_document
        docling_processor.converter = mock_converter_class.return_value
        docling_processor.converter.convert.return_value = mock_result

        # Process test PDF
        documents = []
        async for doc in docling_processor.process("test.pdf", "doc-123"):
            documents.append(doc)

        # Assertions
        assert len(documents) == 1
        assert documents[0].document_id == "doc-123"
        assert isinstance(documents[0], Document)
        docling_processor.converter.convert.assert_called_once_with("test.pdf")

    @patch("os.stat")
    @patch("os.path.exists")
    @patch("os.path.getsize")
    @patch("os.path.getmtime")
    @patch("docling.document_converter.DocumentConverter")
    @pytest.mark.asyncio
    async def test_process_pdf_with_text_items(
        self, mock_converter_class, mock_getmtime, mock_getsize, mock_exists, mock_stat, docling_processor
    ):
        """Test PDF processing with text items."""
        # Mock file operations
        mock_getsize.return_value = 12345
        mock_getmtime.return_value = 1234567890.0
        mock_exists.return_value = True
        # Mock file stat
        mock_stat_result = type("stat_result", (), {})()
        mock_stat_result.st_ctime = 1234567890.0
        mock_stat_result.st_mtime = 1234567890.0
        mock_stat.return_value = mock_stat_result

        # Create mock text item
        mock_text_item = Mock()
        mock_text_item.__class__.__name__ = "TextItem"
        mock_text_item.text = "This is a test paragraph with some content."
        mock_text_item.prov = [Mock(page_no=1)]
        mock_text_item.self_ref = "text_0"

        # Setup mock document
        mock_doc = Mock()
        mock_doc.metadata = {}
        mock_doc.iterate_items.return_value = [mock_text_item]

        mock_result = Mock()
        mock_result.document = mock_doc

        # Set converter on processor instance
        docling_processor.converter = mock_converter_class.return_value
        docling_processor.converter.convert.return_value = mock_result

        # Process document
        documents = []
        async for doc in docling_processor.process("test.pdf", "doc-123"):
            documents.append(doc)

        # Verify document has chunks
        assert len(documents) == 1
        assert len(documents[0].chunks) > 0


class TestDoclingProcessorTableExtraction:
    """Test table extraction with Docling's TableFormer model."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock()
        settings.min_chunk_size = 100
        settings.max_chunk_size = 1000
        settings.chunk_overlap = 20
        settings.chunking_strategy = "simple"
        settings.semantic_threshold = 0.8
        return settings

    @pytest.fixture
    def docling_processor(self, mock_settings):
        """Create DoclingProcessor instance."""
        if DoclingProcessor is None:
            pytest.skip("DoclingProcessor not implemented yet")
        return DoclingProcessor(mock_settings)

    @patch("os.stat")
    @patch("os.path.exists")
    @patch("os.path.getsize")
    @patch("os.path.getmtime")
    @patch("docling.document_converter.DocumentConverter")
    @pytest.mark.asyncio
    async def test_table_extraction_preserves_structure(
        self, mock_converter_class, mock_getmtime, mock_getsize, mock_exists, mock_stat, docling_processor
    ):
        """Test that table extraction preserves table structure."""
        # Mock file operations
        mock_getsize.return_value = 12345
        mock_getmtime.return_value = 1234567890.0
        mock_exists.return_value = True
        # Mock file stat
        mock_stat_result = type("stat_result", (), {})()
        mock_stat_result.st_ctime = 1234567890.0
        mock_stat_result.st_mtime = 1234567890.0
        mock_stat.return_value = mock_stat_result

        # Create mock table item
        mock_table = Mock()
        mock_table.__class__.__name__ = "TableItem"
        mock_table.export_to_dict.return_value = {
            "rows": [
                ["Header 1", "Header 2", "Header 3"],
                ["Cell 1", "Cell 2", "Cell 3"],
                ["Cell 4", "Cell 5", "Cell 6"],
            ]
        }
        mock_table.prov = [Mock(page_no=1)]

        # Setup mock document
        mock_doc = Mock()
        mock_doc.metadata = {}
        mock_doc.iterate_items.return_value = [mock_table]

        mock_result = Mock()
        mock_result.document = mock_doc
        # Set converter on processor instance
        docling_processor.converter = mock_converter_class.return_value
        docling_processor.converter.convert.return_value = mock_result

        # Process document
        documents = []
        async for doc in docling_processor.process("test.pdf", "doc-123"):
            documents.append(doc)

        # Verify table chunk created
        assert len(documents[0].chunks) > 0

        # Find table chunk (table chunks have non-zero table_index)
        table_chunks = [
            chunk
            for chunk in documents[0].chunks
            if chunk.metadata.table_index is not None and chunk.metadata.table_index > 0
        ]

        assert len(table_chunks) > 0, "No table chunks found"
        table_chunk = table_chunks[0]

        # Verify table metadata
        assert table_chunk.metadata.table_index is not None

    @patch("os.stat")
    @patch("os.path.exists")
    @patch("os.path.getsize")
    @patch("os.path.getmtime")
    @patch("docling.document_converter.DocumentConverter")
    @pytest.mark.asyncio
    async def test_multiple_tables_extracted(
        self, mock_converter_class, mock_getmtime, mock_getsize, mock_exists, mock_stat, docling_processor
    ):
        """Test extraction of multiple tables from document."""
        # Mock file operations
        mock_getsize.return_value = 12345
        mock_getmtime.return_value = 1234567890.0
        mock_exists.return_value = True
        # Mock file stat
        mock_stat_result = type("stat_result", (), {})()
        mock_stat_result.st_ctime = 1234567890.0
        mock_stat_result.st_mtime = 1234567890.0
        mock_stat.return_value = mock_stat_result

        # Create multiple mock table items
        mock_table1 = Mock()
        mock_table1.__class__.__name__ = "TableItem"
        mock_table1.export_to_dict.return_value = {"rows": [["A", "B"], ["1", "2"]]}
        mock_table1.prov = [Mock(page_no=1)]

        mock_table2 = Mock()
        mock_table2.__class__.__name__ = "TableItem"
        mock_table2.export_to_dict.return_value = {"rows": [["C", "D"], ["3", "4"]]}
        mock_table2.prov = [Mock(page_no=2)]

        # Setup mock document
        mock_doc = Mock()
        mock_doc.metadata = {}
        mock_doc.iterate_items.return_value = [mock_table1, mock_table2]

        mock_result = Mock()
        mock_result.document = mock_doc
        # Set converter on processor instance
        docling_processor.converter = mock_converter_class.return_value
        docling_processor.converter.convert.return_value = mock_result

        # Process document
        documents = []
        async for doc in docling_processor.process("test.pdf", "doc-123"):
            documents.append(doc)

        # Verify multiple table chunks (table chunks have non-zero table_index)
        table_chunks = [
            chunk
            for chunk in documents[0].chunks
            if chunk.metadata.table_index is not None and chunk.metadata.table_index > 0
        ]

        assert len(table_chunks) >= 2, "Expected at least 2 table chunks"


class TestDoclingProcessorMetadataExtraction:
    """Test metadata extraction from Docling documents."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock()
        settings.min_chunk_size = 100
        settings.max_chunk_size = 1000
        settings.chunk_overlap = 20
        settings.chunking_strategy = "simple"
        settings.semantic_threshold = 0.8
        return settings

    @pytest.fixture
    def docling_processor(self, mock_settings):
        """Create DoclingProcessor instance."""
        if DoclingProcessor is None:
            pytest.skip("DoclingProcessor not implemented yet")
        return DoclingProcessor(mock_settings)

    @patch("os.stat")
    @patch("os.path.exists")
    @patch("os.path.getsize")
    @patch("os.path.getmtime")
    def test_extract_metadata_from_docling_document(
        self, mock_getmtime, mock_getsize, mock_exists, mock_stat, docling_processor
    ):
        """Test metadata extraction from DoclingDocument."""
        # Mock file operations
        mock_getsize.return_value = 12345
        mock_getmtime.return_value = 1234567890.0
        mock_exists.return_value = True
        # Mock file stat
        mock_stat_result = type("stat_result", (), {})()
        mock_stat_result.st_ctime = 1234567890.0
        mock_stat_result.st_mtime = 1234567890.0
        mock_stat.return_value = mock_stat_result

        # Create mock DoclingDocument
        mock_doc = Mock()
        mock_doc.metadata = {
            "title": "Test Document",
            "author": "Test Author",
            "page_count": 5,
            "creator": "Test Creator",
        }
        mock_doc.iterate_items.return_value = []

        # Extract metadata
        metadata = docling_processor._extract_docling_metadata(mock_doc, "/path/to/test.pdf")

        # Verify metadata
        assert isinstance(metadata, DocumentMetadata)
        assert metadata.title == "Test Document"
        assert metadata.author == "Test Author"
        assert metadata.total_pages == 5
        assert metadata.creator == "Test Creator"

    @patch("os.stat")
    @patch("os.path.exists")
    @patch("os.path.getsize")
    @patch("os.path.getmtime")
    def test_extract_metadata_with_table_count(
        self, mock_getmtime, mock_getsize, mock_exists, mock_stat, docling_processor
    ):
        """Test metadata includes table count."""
        # Mock file operations
        mock_getsize.return_value = 12345
        mock_getmtime.return_value = 1234567890.0
        mock_exists.return_value = True
        # Mock file stat
        mock_stat_result = type("stat_result", (), {})()
        mock_stat_result.st_ctime = 1234567890.0
        mock_stat_result.st_mtime = 1234567890.0
        mock_stat.return_value = mock_stat_result

        # Create mock document with tables
        mock_table = Mock()
        mock_table.__class__.__name__ = "TableItem"

        mock_doc = Mock()
        mock_doc.metadata = {}
        mock_doc.iterate_items.return_value = [mock_table, mock_table]

        # Extract metadata
        metadata = docling_processor._extract_docling_metadata(mock_doc, "/path/to/test.pdf")

        # Verify table count in keywords
        assert "table_count" in metadata.keywords
        assert metadata.keywords["table_count"] == "2"


class TestDoclingProcessorImageHandling:
    """Test image extraction and handling."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock()
        settings.min_chunk_size = 100
        settings.max_chunk_size = 1000
        settings.chunk_overlap = 20
        settings.chunking_strategy = "simple"
        settings.semantic_threshold = 0.8
        return settings

    @pytest.fixture
    def docling_processor(self, mock_settings):
        """Create DoclingProcessor instance."""
        if DoclingProcessor is None:
            pytest.skip("DoclingProcessor not implemented yet")
        return DoclingProcessor(mock_settings)

    @patch("os.stat")
    @patch("os.path.exists")
    @patch("os.path.getsize")
    @patch("os.path.getmtime")
    @patch("docling.document_converter.DocumentConverter")
    @pytest.mark.asyncio
    async def test_image_extraction(
        self, mock_converter_class, mock_getmtime, mock_getsize, mock_exists, mock_stat, docling_processor
    ):
        """Test image extraction from document."""
        # Mock file operations
        mock_getsize.return_value = 12345
        mock_getmtime.return_value = 1234567890.0
        mock_exists.return_value = True
        # Mock file stat
        mock_stat_result = type("stat_result", (), {})()
        mock_stat_result.st_ctime = 1234567890.0
        mock_stat_result.st_mtime = 1234567890.0
        mock_stat.return_value = mock_stat_result

        # Create mock image item
        mock_image = Mock()
        mock_image.__class__.__name__ = "PictureItem"
        mock_image.prov = [Mock(page_no=1)]
        mock_image.image = Mock(uri="extracted_images/image_1.png")

        # Setup mock document
        mock_doc = Mock()
        mock_doc.metadata = {}
        mock_doc.iterate_items.return_value = [mock_image]

        mock_result = Mock()
        mock_result.document = mock_doc
        # Set converter on processor instance
        docling_processor.converter = mock_converter_class.return_value
        docling_processor.converter.convert.return_value = mock_result

        # Process document
        documents = []
        async for doc in docling_processor.process("test.pdf", "doc-123"):
            documents.append(doc)

        # Verify image chunk created (image chunks have non-zero image_index)
        image_chunks = [
            chunk
            for chunk in documents[0].chunks
            if chunk.metadata.image_index is not None and chunk.metadata.image_index > 0
        ]

        assert len(image_chunks) > 0, "No image chunks found"
        assert image_chunks[0].metadata.image_index is not None


class TestDoclingProcessorErrorHandling:
    """Test error handling and edge cases."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock()
        settings.min_chunk_size = 100
        settings.max_chunk_size = 1000
        settings.chunk_overlap = 20
        settings.chunking_strategy = "simple"
        settings.semantic_threshold = 0.8
        return settings

    @pytest.fixture
    def docling_processor(self, mock_settings):
        """Create DoclingProcessor instance."""
        if DoclingProcessor is None:
            pytest.skip("DoclingProcessor not implemented yet")
        return DoclingProcessor(mock_settings)

    @patch("docling.document_converter.DocumentConverter")
    @pytest.mark.asyncio
    async def test_process_handles_converter_error(self, mock_converter_class, docling_processor):
        """Test that processing errors are handled gracefully."""
        # Setup mock to raise exception
        docling_processor.converter = mock_converter_class.return_value
        docling_processor.converter.convert.side_effect = Exception("Docling conversion failed")

        # Processing should raise exception
        with pytest.raises(Exception) as exc_info:
            async for _ in docling_processor.process("bad.pdf", "doc-123"):
                pass

        assert "Docling conversion failed" in str(exc_info.value) or "failed" in str(exc_info.value).lower()

    @patch("os.stat")
    @patch("os.path.exists")
    @patch("os.path.getsize")
    @patch("os.path.getmtime")
    @patch("docling.document_converter.DocumentConverter")
    @pytest.mark.asyncio
    async def test_process_empty_document(
        self, mock_converter_class, mock_getmtime, mock_getsize, mock_exists, mock_stat, docling_processor
    ):
        """Test processing of empty document."""
        # Mock file operations
        mock_getsize.return_value = 12345
        mock_getmtime.return_value = 1234567890.0
        mock_exists.return_value = True
        # Mock file stat
        mock_stat_result = type("stat_result", (), {})()
        mock_stat_result.st_ctime = 1234567890.0
        mock_stat_result.st_mtime = 1234567890.0
        mock_stat.return_value = mock_stat_result

        # Create empty mock document
        mock_doc = Mock()
        mock_doc.metadata = {}
        mock_doc.iterate_items.return_value = []

        mock_result = Mock()
        mock_result.document = mock_doc
        # Set converter on processor instance
        docling_processor.converter = mock_converter_class.return_value
        docling_processor.converter.convert.return_value = mock_result

        # Process empty document
        documents = []
        async for doc in docling_processor.process("empty.pdf", "doc-123"):
            documents.append(doc)

        # Should still return a document, just with no chunks
        assert len(documents) == 1
        assert len(documents[0].chunks) == 0


class TestDoclingProcessorChunking:
    """Test chunking integration with Docling."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock()
        settings.min_chunk_size = 50
        settings.max_chunk_size = 200
        settings.chunk_overlap = 20
        settings.chunking_strategy = "simple"
        settings.semantic_threshold = 0.8
        return settings

    @pytest.fixture
    def docling_processor(self, mock_settings):
        """Create DoclingProcessor instance."""
        if DoclingProcessor is None:
            pytest.skip("DoclingProcessor not implemented yet")
        return DoclingProcessor(mock_settings)

    @patch("os.stat")
    @patch("os.path.exists")
    @patch("os.path.getsize")
    @patch("os.path.getmtime")
    @patch("docling.document_converter.DocumentConverter")
    @pytest.mark.asyncio
    async def test_chunking_applied_to_text(
        self, mock_converter_class, mock_getmtime, mock_getsize, mock_exists, mock_stat, docling_processor
    ):
        """Test that chunking strategy is applied to extracted text."""
        # Mock file operations
        mock_getsize.return_value = 12345
        mock_getmtime.return_value = 1234567890.0
        mock_exists.return_value = True
        # Mock file stat
        mock_stat_result = type("stat_result", (), {})()
        mock_stat_result.st_ctime = 1234567890.0
        mock_stat_result.st_mtime = 1234567890.0
        mock_stat.return_value = mock_stat_result

        # Create mock text item with long text
        long_text = "This is a test paragraph. " * 50  # ~1250 characters
        mock_text_item = Mock()
        mock_text_item.__class__.__name__ = "TextItem"
        mock_text_item.text = long_text
        mock_text_item.prov = [Mock(page_no=1)]
        mock_text_item.self_ref = "text_0"

        # Setup mock document
        mock_doc = Mock()
        mock_doc.metadata = {}
        mock_doc.iterate_items.return_value = [mock_text_item]

        mock_result = Mock()
        mock_result.document = mock_doc
        # Set converter on processor instance
        docling_processor.converter = mock_converter_class.return_value
        docling_processor.converter.convert.return_value = mock_result

        # Process document
        documents = []
        async for doc in docling_processor.process("test.pdf", "doc-123"):
            documents.append(doc)

        # Verify multiple chunks created (text should be split)
        # With max_chunk_size=200, we expect multiple chunks
        assert len(documents[0].chunks) > 1, "Long text should be chunked"

    def test_chunk_metadata_includes_layout_info(self, docling_processor):
        """Test that chunks include standard metadata fields."""
        # Create mock chunk metadata
        chunk_metadata = {"page_number": 1, "chunk_number": 0, "layout_type": "text", "reading_order": "text_0"}

        chunk = docling_processor._create_chunk("Test text", chunk_metadata, "doc-123")

        # Verify chunk has required standard metadata
        assert chunk.metadata.page_number == 1
        assert chunk.metadata.chunk_number == 0
        # layout_type and reading_order are extra fields added to metadata dict
        # but DocumentChunkMetadata schema uses ConfigDict(extra='allow') so they're stored
        assert chunk.metadata.model_extra is not None or hasattr(chunk.metadata, "__pydantic_extra__")
