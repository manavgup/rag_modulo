"""Word document processor.

This module provides functionality for processing Microsoft Word documents,
extracting text content and creating document chunks.
"""

import logging
import os
from collections.abc import AsyncIterator

from core.custom_exceptions import DocumentProcessingError
from core.identity_service import IdentityService
from docx import Document as DocxDocument
from vectordbs.data_types import Document

from rag_solution.data_ingestion.base_processor import BaseProcessor
from rag_solution.doc_utils import get_document

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class WordProcessor(BaseProcessor):
    """
    Processor for reading and chunking Word documents.

    Methods:
        process(file_path: str) -> AsyncIterable[Document]: Process the Word document and yield Document instances.
    """

    async def process(self, file_path: str, _document_id: str) -> AsyncIterator[Document]:
        """
        Process the Word document and yield Document instances.

        Args:
            file_path (str): The path to the Word document to be processed.
            document_id (str): The ID of the document being processed.

        Yields:
            Document: An instance of Document containing the processed data.

        Raises:
            DocumentProcessingError: If there is an error processing the Word document.
        """
        try:
            doc = DocxDocument(file_path)
            full_text = []

            for paragraph in doc.paragraphs:
                full_text.append(paragraph.text)

            text = "\n".join(full_text)
            chunks = self.chunking_method(text)

            for chunk in chunks:
                yield get_document(
                    name=os.path.basename(file_path), document_id=IdentityService.generate_document_id(), text=chunk
                )
        except Exception as e:
            logger.error("Error reading Word file %s: %s", file_path, e, exc_info=True)
            raise DocumentProcessingError(
                doc_id=file_path,
                error_type="processing_failed",
                message=f"Error processing Word file {file_path}",
                details={"error": str(e)},
            ) from e
