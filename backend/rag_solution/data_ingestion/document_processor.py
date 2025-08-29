import logging
import multiprocessing
import os
from collections.abc import AsyncIterable
from multiprocessing.managers import SyncManager
from typing import Any

from core.custom_exceptions import DocumentProcessingError
from rag_solution.data_ingestion.base_processor import BaseProcessor
from rag_solution.data_ingestion.excel_processor import ExcelProcessor
from rag_solution.data_ingestion.pdf_processor import PdfProcessor
from rag_solution.data_ingestion.txt_processor import TxtProcessor
from rag_solution.data_ingestion.word_processor import WordProcessor
from vectordbs.data_types import Document

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class DocumentProcessor:
    """
    Class to process documents based on their file type and generate suggested questions.

    Attributes:
        processors (Dict[str, BaseProcessor]): A dictionary mapping file extensions to their respective processors.
        question_service (QuestionService): Service for generating suggested questions.
    """

    def __init__(self, manager: SyncManager | None = None):
        """
        Initialize the document processor.

        Args:
            manager (Optional[SyncManager]): Multiprocessing manager for shared resources
            question_service (Optional[QuestionService]): Service for question operations
        """
        if manager is None:
            manager = multiprocessing.Manager()
        self.manager = manager
        self.processors: dict[str, BaseProcessor] = {
            ".txt": TxtProcessor(),
            ".pdf": PdfProcessor(self.manager),
            ".docx": WordProcessor(),
            ".xlsx": ExcelProcessor(),
        }

    async def _process_async(self, processor: BaseProcessor, file_path: str, document_id: str) -> list[Document]:
        """
        Process document asynchronously.

        Args:
            processor: Document processor to use
            file_path: Path to the document

        Returns:
            List of processed documents
        """
        documents = []
        async for doc in processor.process(file_path, document_id):
            documents.append(doc)
        return documents

    async def process_document(self, file_path: str, document_id: str) -> AsyncIterable[Document]:
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
                logger.warning(f"No processor found for file extension: {file_extension}")
                return

            # Process the document asynchronously
            documents = await self._process_async(processor, file_path, document_id)

            # Yield documents
            for doc in documents:
                yield doc

        except Exception as e:
            logger.error(f"Error processing document {file_path}: {e}", exc_info=True)
            raise DocumentProcessingError(
                doc_id=document_id,
                error_type="DocumentProcessingError",
                message=f"Error processing document {file_path}",
            ) from e

    def extract_metadata_from_processor(self, file_path: str) -> dict[str, Any]:
        """
        Extract metadata from a document using its processor.

        Args:
            file_path (str): Path to the document

        Returns:
            Dict[str, Any]: Extracted metadata

        Raises:
            ValueError: If file type is not supported
        """
        file_extension = os.path.splitext(file_path)[1].lower()
        processor = self.processors.get(file_extension)
        if processor:
            return processor.extract_metadata(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
