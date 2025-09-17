"""Document processor for handling multiple file types.

This module provides a unified interface for processing different document types
including PDF, Word, Excel, and text files.
"""

import logging
import multiprocessing
import os
from collections.abc import AsyncGenerator
from multiprocessing.managers import SyncManager
from typing import Any

from core.config import Settings, get_settings
from core.custom_exceptions import DocumentProcessingError
from vectordbs.data_types import Document, DocumentMetadata

from rag_solution.data_ingestion.base_processor import BaseProcessor
from rag_solution.data_ingestion.excel_processor import ExcelProcessor
from rag_solution.data_ingestion.pdf_processor import PdfProcessor
from rag_solution.data_ingestion.txt_processor import TxtProcessor
from rag_solution.data_ingestion.word_processor import WordProcessor

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class DocumentProcessor:
    """
    Class to process documents based on their file type and generate suggested questions.

    Attributes:
        processors (Dict[str, BaseProcessor]): A dictionary mapping file extensions to their respective processors.
        question_service (QuestionService): Service for generating suggested questions.
    """

    def __init__(self: Any, manager: SyncManager | None = None, settings: Settings = get_settings()) -> None:
        """
        Initialize the document processor.

        Args:
            manager (Optional[SyncManager]): Multiprocessing manager for shared resources
            settings (Settings): Settings object for dependency injection
        """
        if manager is None:
            manager = multiprocessing.Manager()
        self.manager = manager
        self.settings = settings
        self.processors: dict[str, BaseProcessor] = {
            ".txt": TxtProcessor(settings),
            ".pdf": PdfProcessor(self.manager, settings),
            ".docx": WordProcessor(settings),
            ".xlsx": ExcelProcessor(settings),
        }

    async def _process_async(self, processor: BaseProcessor, file_path: str, document_id: str) -> list[Document]:
        """
        Process document asynchronously.

        Args:
            processor: Document processor to use
            file_path: Path to the document
            document_id: ID of the document being processed

        Returns:
            List of processed documents
        """
        documents = []
        async for doc in processor.process(file_path, document_id):
            documents.append(doc)
        return documents

    async def process_document(self, file_path: str, document_id: str) -> AsyncGenerator[Document, None]:
        """
        Process a document based on its file extension and generate suggested questions.

        Args:
            file_path (str): The path to the file to be processed.

        Yields:
            Document: A processed Document object.

        Raises:
            DocumentProcessingError: If there is an error processing the document.
        """
        try:
            file_extension = os.path.splitext(file_path)[1].lower()
            processor = self.processors.get(file_extension)

            if not processor:
                logger.warning("No processor found for file extension: %s", file_extension)
                return

            # Process the document asynchronously
            documents = await self._process_async(processor, file_path, document_id)

            # Yield documents
            for doc in documents:
                yield doc

        except Exception as e:
            logger.error("Error processing document %s: %s", file_path, e, exc_info=True)
            raise DocumentProcessingError(
                doc_id=document_id,
                error_type="DocumentProcessingError",
                message=f"Error processing document {file_path}",
            ) from e

    def extract_metadata_from_processor(self, file_path: str) -> DocumentMetadata:
        """
        Extract metadata from a document using its processor.

        Args:
            file_path (str): Path to the document

        Returns:
            DocumentMetadata: Extracted metadata

        Raises:
            ValueError: If file type is not supported
        """
        file_extension = os.path.splitext(file_path)[1].lower()
        processor = self.processors.get(file_extension)
        if processor:
            return processor.extract_metadata(file_path)
        raise ValueError(f"Unsupported file type: {file_extension}")
