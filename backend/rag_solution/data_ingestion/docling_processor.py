"""IBM Docling document processor adapter.

This module provides a unified document processor using IBM's Docling library
for advanced document processing capabilities including AI-powered table extraction,
layout analysis, and reading order detection.
"""

# Standard library imports
import logging
import os
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

# Third-party imports
from docling.document_converter import DocumentConverter
from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
from transformers import AutoTokenizer, PreTrainedTokenizerBase

# First-party imports
from core.config import Settings
from core.identity_service import IdentityService
from rag_solution.data_ingestion.base_processor import BaseProcessor
from vectordbs.data_types import Document, DocumentChunk, DocumentChunkMetadata, DocumentMetadata

logger = logging.getLogger(__name__)


class DoclingProcessor(BaseProcessor):
    """Unified document processor using IBM Docling.

    Supports: PDF, DOCX, PPTX, HTML, images with AI-powered
    table extraction, layout analysis, and reading order detection.

    Attributes:
        converter: Docling document converter
        chunker: HybridChunker for token-aware chunking
        tokenizer: HuggingFace tokenizer for token counting
    """

    converter: DocumentConverter | None = None
    chunker: HybridChunker | None = None
    tokenizer: PreTrainedTokenizerBase | None = None

    def __init__(self, settings: Settings) -> None:
        """Initialize Docling processor with hybrid chunking.

        Args:
            settings: Application settings
        """
        super().__init__(settings)

        # Initialize Docling converter
        try:
            self.converter = DocumentConverter()

            # IBM Slate/Granite embeddings have 512 token limit
            # Use configurable max_tokens (default 400 = 78% of 512) to provide safety margin:
            # - Uses IBM Granite tokenizer (same model family as IBM Slate embeddings)
            # - Ensures accurate token counting that matches embedding model
            # - Allows room for metadata/headers in embedding requests (512 - 400 = 112)
            # - Granite tokenizer supports up to 8192, but we limit to 512 for embedding quality
            max_tokens = min(settings.max_chunk_size, settings.chunking_max_tokens)

            # Initialize tokenizer for HybridChunker from settings
            # This ensures token counts match what the embedding model will see
            # Default: ibm-granite/granite-embedding-english-r2 (matches IBM Slate family)
            try:
                # Pin revision to prevent unsafe downloads (Bandit B615)
                # Note: revision="main" pins to branch; for production, consider pinning to specific commit hash
                granite_tokenizer = AutoTokenizer.from_pretrained(
                    settings.chunking_tokenizer_model,
                    revision="main",  # nosec B615
                )
            except Exception as e:
                logger.error(
                    "Failed to load tokenizer '%s': %s. Check CHUNKING_TOKENIZER_MODEL setting and network connectivity.",
                    settings.chunking_tokenizer_model,
                    e,
                )
                raise ValueError(
                    f"Cannot initialize DoclingProcessor: tokenizer '{settings.chunking_tokenizer_model}' not available. "
                    f"Ensure the model exists on HuggingFace and you have network connectivity. "
                    f"Error: {e}"
                ) from e

            # Configure hybrid chunker with IBM Granite tokenizer
            # Using the actual embedding model's tokenizer eliminates token count mismatches
            self.chunker = HybridChunker(
                tokenizer=granite_tokenizer,  # Use IBM Granite tokenizer for accurate counts
                max_tokens=max_tokens,  # Enforced with correct tokenization
                merge_peers=True,  # Merge similar semantic chunks
            )
            self.tokenizer = granite_tokenizer  # Store for statistics

            logger.info(
                "DoclingProcessor initialized with HybridChunker (max_tokens=%d, tokenizer=%s)",
                max_tokens,
                settings.chunking_tokenizer_model,
            )
        except ImportError as e:
            logger.warning("Docling not installed: %s. Install with: pip install docling", e)
            # Create a mock converter for testing
            self.converter = None
            self.chunker = None
            self.tokenizer = None

    async def process(self, file_path: str, document_id: str) -> AsyncIterator[Document]:
        """Process document using Docling.

        Args:
            file_path: Path to the document file
            document_id: Unique document identifier

        Yields:
            Document objects with processed chunks

        Raises:
            Exception: If processing fails
        """
        logger.info("Processing document with Docling: %s", file_path)

        try:
            if self.converter is None:
                raise ImportError("Docling DocumentConverter not available")

            # Convert document using Docling
            result = self.converter.convert(file_path)

            # Extract metadata
            metadata = self._extract_docling_metadata(result.document, file_path)

            # Convert to RAG Modulo Document format
            chunks = await self._convert_to_chunks(result.document, document_id)

            # Update total chunks in metadata
            metadata.total_chunks = len(chunks)

            # Yield single Document with all chunks
            yield Document(
                name=os.path.basename(file_path),
                document_id=document_id,
                chunks=chunks,
                path=file_path,
                metadata=metadata,
            )

        except Exception as e:
            logger.error("Docling processing failed for %s: %s", file_path, e, exc_info=True)
            raise

    def _extract_docling_metadata(self, docling_doc: Any, file_path: str) -> DocumentMetadata:
        """Extract metadata from DoclingDocument.

        Args:
            docling_doc: Docling document object
            file_path: Original file path

        Returns:
            DocumentMetadata object
        """
        # Get base metadata from parent class
        base_metadata = super().extract_metadata(file_path)

        # Extract Docling-specific metadata
        doc_meta = {}
        if hasattr(docling_doc, "metadata"):
            doc_meta = docling_doc.metadata if isinstance(docling_doc.metadata, dict) else {}

        # Count document elements
        table_count = 0
        image_count = 0

        if hasattr(docling_doc, "iterate_items"):
            for item in docling_doc.iterate_items():
                item_type = type(item).__name__
                if item_type == "TableItem":
                    table_count += 1
                elif item_type == "PictureItem":
                    image_count += 1

        # Build keywords with document stats
        keywords: dict[str, Any] = {
            "table_count": str(table_count),
            "image_count": str(image_count),
        }
        # Merge existing keywords if they're a dict
        if isinstance(base_metadata.keywords, dict):
            keywords.update(base_metadata.keywords)

        return DocumentMetadata(
            document_name=base_metadata.document_name,
            title=doc_meta.get("title") or base_metadata.document_name,
            author=doc_meta.get("author"),
            subject=doc_meta.get("subject"),
            keywords=keywords,
            creator=doc_meta.get("creator"),
            producer="IBM Docling",
            creation_date=(
                datetime.fromisoformat(doc_meta["creation_date"])
                if "creation_date" in doc_meta
                else base_metadata.creation_date
            ),
            mod_date=base_metadata.mod_date,
            total_pages=doc_meta.get("page_count"),
            total_chunks=None,  # Set during processing
        )

    async def _convert_to_chunks(self, docling_doc: Any, document_id: str) -> list[DocumentChunk]:
        """Convert DoclingDocument to RAG Modulo chunks using Docling's HybridChunker.

        Args:
            docling_doc: Docling document object
            document_id: Document identifier

        Returns:
            List of DocumentChunk objects
        """
        if self.chunker is None:
            logger.error("HybridChunker not initialized - falling back to old method")
            return await self._convert_to_chunks_legacy(docling_doc, document_id)

        chunks: list[DocumentChunk] = []
        token_counts: list[int] = []  # Track token counts for statistics

        # Use Docling's hybrid chunker - it handles the entire document intelligently
        docling_chunks = list(self.chunker.chunk(dl_doc=docling_doc))

        logger.info("Docling HybridChunker created %d chunks", len(docling_chunks))

        for chunk_idx, docling_chunk in enumerate(docling_chunks):
            # Extract text from DoclingChunk
            chunk_text = docling_chunk.text

            # Count tokens using IBM Granite tokenizer for accurate statistics
            # This matches the token counting used during chunking
            # Uses encode() with add_special_tokens=True to match what embedding model sees
            try:
                if self.tokenizer is None:
                    raise AttributeError("Tokenizer not initialized")
                token_count = len(self.tokenizer.encode(chunk_text, add_special_tokens=True))
            except (Exception, AttributeError) as e:
                # Fallback: estimate tokens using rough 4-char-per-token heuristic
                logger.warning("Token counting failed for chunk %d: %s. Using estimation.", chunk_idx, e)
                token_count = len(chunk_text) // 4
            token_counts.append(token_count)

            # Extract metadata from DoclingChunk
            # Extract all unique page numbers from all doc_items (for multi-page chunks)
            page_numbers = set()
            if hasattr(docling_chunk, "meta") and hasattr(docling_chunk.meta, "doc_items"):
                doc_items = docling_chunk.meta.doc_items
                for item in doc_items:
                    # DocItem has prov attribute which is a list of Provenance objects
                    if hasattr(item, "prov") and item.prov:
                        for prov in item.prov:
                            page_no = getattr(prov, "page_no", None)
                            if page_no is not None:
                                page_numbers.add(page_no)

            # Use first page for backwards compatibility, but store all pages in metadata
            page_number = min(page_numbers) if page_numbers else None

            chunk_metadata = {
                "page_number": page_number,
                "chunk_number": chunk_idx,
                "start_index": 0,
                "end_index": len(chunk_text),
                "table_index": 0,
                "image_index": 0,
                "layout_type": "hybrid",
                "headings": getattr(docling_chunk.meta, "headings", []) if hasattr(docling_chunk, "meta") else [],
                "page_range": sorted(page_numbers) if len(page_numbers) > 1 else None,  # For multi-page chunks
            }

            chunks.append(self._create_chunk(chunk_text, chunk_metadata, document_id))

        # Log chunking statistics
        if token_counts:
            avg_tokens = sum(token_counts) / len(token_counts)
            max_tokens = max(token_counts)
            logger.info(
                "Chunking complete: %d chunks, avg %.0f tokens, max %d tokens",
                len(chunks),
                avg_tokens,
                max_tokens,
            )

        return chunks

    async def _convert_to_chunks_legacy(self, docling_doc: Any, document_id: str) -> list[DocumentChunk]:
        """Legacy chunking method (fallback if HybridChunker not available).

        Args:
            docling_doc: Docling document object
            document_id: Document identifier

        Returns:
            List of DocumentChunk objects
        """
        chunks: list[DocumentChunk] = []
        chunk_counter = 0
        table_counter = 0
        image_counter = 0

        # Check if document has iterate_items method
        if not hasattr(docling_doc, "iterate_items"):
            logger.warning("DoclingDocument missing iterate_items method")
            return chunks

        # Iterate through document items (structure-aware)
        for item_data in docling_doc.iterate_items():
            # Handle both old API (direct items) and new API (tuples)
            item = item_data[0] if isinstance(item_data, tuple) else item_data
            item_type = type(item).__name__

            # Handle text blocks
            if item_type in ("TextItem", "SectionHeaderItem", "ListItem", "CodeItem"):
                text_content = getattr(item, "text", "")
                if not text_content:
                    continue

                # Apply old chunking strategy
                text_chunks = self.chunking_method(text_content)

                for chunk_text in text_chunks:
                    chunk_metadata = {
                        "page_number": self._get_page_number(item),
                        "chunk_number": chunk_counter,
                        "start_index": 0,
                        "end_index": len(chunk_text),
                        "table_index": 0,
                        "image_index": 0,
                        "layout_type": "text",
                        "reading_order": getattr(item, "self_ref", None),
                    }

                    chunks.append(self._create_chunk(chunk_text, chunk_metadata, document_id))
                    chunk_counter += 1

            # Handle tables
            elif item_type == "TableItem":
                table_data = None
                if hasattr(item, "export_to_dict"):
                    table_data = item.export_to_dict()

                table_text = self._table_to_text(table_data) if table_data else "Table content"
                table_counter += 1
                chunk_metadata = {
                    "page_number": self._get_page_number(item),
                    "chunk_number": chunk_counter,
                    "start_index": 0,
                    "end_index": len(table_text),
                    "table_index": table_counter,
                    "image_index": 0,
                    "layout_type": "table",
                    "table_data": table_data,
                }

                chunks.append(self._create_chunk(table_text, chunk_metadata, document_id))
                chunk_counter += 1

            # Handle images
            elif item_type == "PictureItem":
                image_path = None
                if hasattr(item, "image") and hasattr(item.image, "uri"):
                    image_path = item.image.uri

                image_counter += 1
                chunk_metadata = {
                    "page_number": self._get_page_number(item),
                    "chunk_number": chunk_counter,
                    "start_index": 0,
                    "end_index": 0,
                    "table_index": 0,
                    "image_index": image_counter,
                    "layout_type": "image",
                    "image_path": image_path,
                }

                image_text = f"Image: {image_path or 'embedded'}"
                chunks.append(self._create_chunk(image_text, chunk_metadata, document_id))
                chunk_counter += 1

        logger.info("Created %d chunks from Docling document", len(chunks))
        return chunks

    def _get_page_number(self, item: Any) -> int | None:
        """Extract page number from Docling item.

        Args:
            item: Docling document item

        Returns:
            Page number (1-indexed) or None
        """
        if hasattr(item, "prov") and item.prov and len(item.prov) > 0:
            # Try new API first (page_no), fallback to old API (page)
            page_no = getattr(item.prov[0], "page_no", None)
            if page_no is not None:
                return int(page_no)
            page = getattr(item.prov[0], "page", None)
            if page is not None:
                return int(page)
        return None

    def _table_to_text(self, table_data: dict) -> str:
        """Convert structured table data to text representation.

        Args:
            table_data: Table data from Docling

        Returns:
            Text representation of table
        """
        if not table_data or "rows" not in table_data:
            return "Empty table"

        rows = table_data["rows"]
        if not rows:
            return "Empty table"

        # Format table as text with | separators
        text_lines = []
        for row in rows:
            text_lines.append(" | ".join(str(cell) for cell in row))

        return "\n".join(text_lines)

    def _create_chunk(self, text: str, metadata: dict[str, Any], document_id: str) -> DocumentChunk:
        """Create DocumentChunk from text and metadata.

        Args:
            text: Chunk text content
            metadata: Chunk metadata dict
            document_id: Document identifier

        Returns:
            DocumentChunk object
        """
        chunk_id = IdentityService.generate_document_id()

        # Create DocumentChunkMetadata with only supported fields
        chunk_metadata_dict = {
            "source": "pdf",  # Use 'pdf' as default source type
            "page_number": metadata.get("page_number"),
            "chunk_number": metadata.get("chunk_number", 0),
            "start_index": metadata.get("start_index", 0),
            "end_index": metadata.get("end_index", 0),
            "table_index": metadata.get("table_index", 0),
            "image_index": metadata.get("image_index", 0),
        }

        # Add optional metadata fields that DocumentChunkMetadata might support
        for key in ["layout_type", "reading_order", "table_data", "image_path"]:
            if key in metadata:
                chunk_metadata_dict[key] = metadata[key]

        return DocumentChunk(
            chunk_id=chunk_id,
            text=text,
            embeddings=[],  # Generated in ingestion pipeline
            metadata=DocumentChunkMetadata(**chunk_metadata_dict),
            document_id=document_id,
        )
