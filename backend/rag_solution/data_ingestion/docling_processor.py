"""IBM Docling document processor adapter.

This module provides a unified document processor using IBM's Docling library
for advanced document processing capabilities including AI-powered table extraction,
layout analysis, and reading order detection.
"""

import logging
import os
import uuid
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

from core.config import Settings
from rag_solution.data_ingestion.base_processor import BaseProcessor
from vectordbs.data_types import Document, DocumentChunk, DocumentChunkMetadata, DocumentMetadata

logger = logging.getLogger(__name__)


class DoclingProcessor(BaseProcessor):
    """Unified document processor using IBM Docling.

    Supports: PDF, DOCX, PPTX, HTML, images with AI-powered
    table extraction, layout analysis, and reading order detection.
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize Docling processor with hybrid chunking.

        Args:
            settings: Application settings
        """
        super().__init__(settings)

        # Import Docling here to avoid import errors when not installed
        try:
            from docling.chunking import HybridChunker
            from docling.document_converter import DocumentConverter
            from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
            from transformers import AutoTokenizer

            self.converter = DocumentConverter()

            # Initialize tokenizer for accurate token counting
            # Use a tokenizer compatible with embedding models
            base_tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")

            # IBM Slate/Granite embeddings have 512 token limit
            max_tokens = min(settings.max_chunk_size, 400)  # Safe limit: 400 tokens (vs 512 max)

            # Wrap tokenizer with HuggingFaceTokenizer (new API)
            self.tokenizer = HuggingFaceTokenizer(
                tokenizer=base_tokenizer,
                max_tokens=max_tokens,
            )

            # Configure hybrid chunker with token limits
            self.chunker = HybridChunker(
                tokenizer=self.tokenizer,
                merge_peers=True,  # Merge similar semantic chunks
            )

            logger.info("DoclingProcessor initialized with HybridChunker (max_tokens=%d)", max_tokens)
        except ImportError as e:
            logger.warning(f"Docling not installed: {e}. Install with: pip install docling")
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

        logger.info(f"Docling HybridChunker created {len(docling_chunks)} chunks")

        for chunk_idx, docling_chunk in enumerate(docling_chunks):
            # Extract text from DoclingChunk
            chunk_text = docling_chunk.text

            # Count actual tokens using the wrapped tokenizer
            # HuggingFaceTokenizer has count_tokens() method
            token_count = self.tokenizer.count_tokens(chunk_text)
            token_counts.append(token_count)

            # Extract metadata from DoclingChunk
            # Try to get page number from chunk metadata
            page_number = None
            if hasattr(docling_chunk, "meta") and hasattr(docling_chunk.meta, "doc_items"):
                doc_items = docling_chunk.meta.doc_items
                if doc_items and len(doc_items) > 0:
                    first_item = doc_items[0]
                    # DocItem has prov attribute which is a list of Provenance objects
                    if hasattr(first_item, "prov") and first_item.prov and len(first_item.prov) > 0:
                        page_number = getattr(first_item.prov[0], "page_no", None)

            chunk_metadata = {
                "page_number": page_number,
                "chunk_number": chunk_idx,
                "start_index": 0,
                "end_index": len(chunk_text),
                "table_index": 0,
                "image_index": 0,
                "layout_type": "hybrid",
                "headings": getattr(docling_chunk.meta, "headings", []) if hasattr(docling_chunk, "meta") else [],
            }

            chunks.append(self._create_chunk(chunk_text, chunk_metadata, document_id))

        # Log chunking statistics
        if token_counts:
            avg_tokens = sum(token_counts) / len(token_counts)
            max_tokens = max(token_counts)
            logger.info(
                f"Chunking complete: {len(chunks)} chunks, avg {avg_tokens:.0f} tokens, max {max_tokens} tokens"
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

    def _get_page_number(self, item: Any) -> int:
        """Extract page number from Docling item.

        Args:
            item: Docling document item

        Returns:
            Page number (1-indexed) or None
        """
        if hasattr(item, "prov") and item.prov and len(item.prov) > 0:
            # Try new API first (page_no), fallback to old API (page)
            return getattr(item.prov[0], "page_no", getattr(item.prov[0], "page", None))
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
        chunk_id = str(uuid.uuid4())

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
