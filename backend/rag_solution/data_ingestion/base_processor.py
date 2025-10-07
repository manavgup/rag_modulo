"""Base processor for document ingestion.

This module provides the abstract base class for all document processors,
handling common functionality like metadata extraction and chunking configuration.
"""

import logging
import os
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from datetime import datetime
from typing import TYPE_CHECKING, Any

from core.config import Settings
from core.identity_service import IdentityService
from rag_solution.data_ingestion.chunking import get_chunking_method
from rag_solution.data_ingestion.hierarchical_chunking import hierarchical_chunker
from vectordbs.data_types import Document, DocumentChunk, DocumentChunkMetadata, DocumentMetadata

if TYPE_CHECKING:
    pass

logging.basicConfig(level=logging.INFO)


class BaseProcessor(ABC):
    """
    Abstract base class for document processors.

    Attributes:
        min_chunk_size (int): Minimum chunk size for chunking documents.
        max_chunk_size (int): Maximum chunk size for chunking documents.
        semantic_threshold (float): Semantic threshold for chunking documents.
        chunking_method: Method used for chunking documents.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.min_chunk_size: int = settings.min_chunk_size
        self.max_chunk_size: int = settings.max_chunk_size
        self.semantic_threshold: float = settings.semantic_threshold
        self.chunking_method = get_chunking_method(settings)
        self.use_hierarchical = settings.chunking_strategy.lower() == "hierarchical"

    def extract_metadata(self, file_path: str) -> DocumentMetadata:
        """
        Extract basic metadata from the file.

        Args:
            file_path (str): The path to the file.

        Returns:
            DocumentMetadata: Metadata object containing file information.

        Raises:
            FileNotFoundError: If the file does not exist.
            PermissionError: If the file cannot be accessed.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        file_stat = os.stat(file_path)
        filename = os.path.basename(file_path)

        return DocumentMetadata(
            document_name=filename,
            title=filename,  # Default to filename if no specific title
            author=None,
            subject=None,
            keywords={},
            creator=None,
            producer=None,
            creation_date=datetime.fromtimestamp(file_stat.st_ctime),
            mod_date=datetime.fromtimestamp(file_stat.st_mtime),
            total_pages=None,  # To be set by specific processors
            total_chunks=None,  # To be set after chunking
        )

    def create_chunks_with_hierarchy(self, text: str, document_id: str, source: Any) -> list[Any]:
        """Create document chunks with hierarchical metadata if enabled.

        Args:
            text: Text to chunk
            document_id: Document ID
            source: Source type for metadata

        Returns:
            List of DocumentChunk objects with hierarchy metadata
        """
        if self.use_hierarchical:
            # Get all hierarchical chunks
            hierarchical_chunks = hierarchical_chunker(text, self.settings)

            # Convert to DocumentChunks with hierarchy metadata
            document_chunks = []
            for h_chunk in hierarchical_chunks:
                chunk_metadata = DocumentChunkMetadata(
                    source=source,
                    document_id=document_id,
                    start_index=h_chunk.start_index,
                    end_index=h_chunk.end_index,
                    parent_chunk_id=h_chunk.parent_id,
                    child_chunk_ids=h_chunk.child_ids,
                    level=h_chunk.level,
                )

                chunk = DocumentChunk(
                    chunk_id=h_chunk.chunk_id,
                    text=h_chunk.text,
                    embeddings=[],
                    document_id=document_id,
                    metadata=chunk_metadata,
                    parent_chunk_id=h_chunk.parent_id,
                    child_chunk_ids=h_chunk.child_ids,
                    level=h_chunk.level,
                )
                document_chunks.append(chunk)

            return document_chunks

        # Standard chunking
        chunk_texts = self.chunking_method(text)
        chunk_metadata = DocumentChunkMetadata(source=source, document_id=document_id)

        document_chunks = []
        for chunk_text in chunk_texts:
            chunk = DocumentChunk(
                chunk_id=IdentityService.generate_document_id(),
                text=chunk_text,
                embeddings=[],
                document_id=document_id,
                metadata=chunk_metadata,
            )
            document_chunks.append(chunk)

        return document_chunks

    @abstractmethod
    def process(self, file_path: str, document_id: str) -> AsyncIterator[Document]:
        """
        Process a document file and generate Document objects.

        This abstract method must be implemented by specific processors to handle
        their respective document types. It should handle the complete document
        processing pipeline including parsing, chunking, and metadata extraction.

        Args:
            file_path: Path to the document file.
            document_id: ID of the document being processed.

        Yields:
            Document: Processed document objects containing chunks and metadata.

        Raises:
            DocumentProcessingError: If there is an error processing the document.
            NotImplementedError: If the processor doesn't implement this method.
        """
