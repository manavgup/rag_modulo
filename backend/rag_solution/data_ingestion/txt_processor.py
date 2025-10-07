"""Text document processor.

This module provides functionality for processing plain text files,
extracting content and creating document chunks.
"""

import logging
import os
from collections.abc import AsyncIterator

import aiofiles

from core.custom_exceptions import DocumentProcessingError
from rag_solution.data_ingestion.base_processor import BaseProcessor

# Embedding functionality inherited from BaseProcessor
from vectordbs.data_types import Document, Source

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class TxtProcessor(BaseProcessor):
    """
    Processor for reading and chunking text files.

    Methods:
        process(file_path: str) -> AsyncIterable[Document]: Process the text file and yield Document instances.
    """

    # pylint: disable=invalid-overridden-method
    # Justification: Base class will be updated to async in future, this is transitional
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

                # Use the base processor's hierarchical-aware chunk creation
                document_chunks = self.create_chunks_with_hierarchy(text, _document_id, Source.OTHER)

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
