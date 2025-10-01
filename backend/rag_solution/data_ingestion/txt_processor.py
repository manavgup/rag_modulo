"""Text document processor.

This module provides functionality for processing plain text files,
extracting content and creating document chunks.
"""

import logging
import os
import uuid
from collections.abc import AsyncIterator

import aiofiles
from core.custom_exceptions import DocumentProcessingError

# Embedding functionality inherited from BaseProcessor
from vectordbs.data_types import Document, DocumentChunk, DocumentChunkMetadata, Source

from rag_solution.data_ingestion.base_processor import BaseProcessor

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class TxtProcessor(BaseProcessor):
    """
    Processor for reading and chunking text files.

    Methods:
        process(file_path: str) -> AsyncIterable[Document]: Process the text file and yield Document instances.
    """

    async def process(self, file_path: str, _document_id: str) -> AsyncIterator[Document]:
        """
        Process the text file and yield Document instances.

        Args:
            file_path (str): The path to the text file to be processed.
            document_id (str): The ID of the document being processed.

        Yields:
            Document: An instance of Document containing the processed data.

        Raises:
            DocumentProcessingError: If there is an error processing the text file.
        """
        try:
            async with aiofiles.open(file_path, encoding="utf-8") as f:
                text = await f.read()
                chunks = self.chunking_method(text)

                # Create one document with all chunks

                # Create chunk metadata for source information
                chunk_metadata = DocumentChunkMetadata(source=Source.OTHER, document_id=_document_id)

                # Create all chunks for this document
                document_chunks = []

                # Create chunks without embeddings (embeddings will be generated in ingestion.py)
                for chunk_text in chunks:
                    chunk = DocumentChunk(
                        chunk_id=str(uuid.uuid4()),
                        text=chunk_text,
                        embeddings=[],  # Empty embeddings
                        document_id=_document_id,
                        metadata=chunk_metadata,
                    )
                    document_chunks.append(chunk)

                # Create one document with all chunks
                document = Document(
                    name=os.path.basename(file_path),
                    document_id=_document_id,
                    chunks=document_chunks,
                    metadata=None,
                )

                yield document
        except Exception as e:
            logger.error("Error processing TXT file %s: %s", file_path, e, exc_info=True)
            raise DocumentProcessingError(
                doc_id=file_path,
                error_type="processing_failed",
                message=f"Error processing TXT file {file_path}",
                details={"error": str(e)},
            ) from e
