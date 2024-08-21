import logging
import os
from typing import Dict, Iterable, Optional, Any
import multiprocessing
from multiprocessing.managers import SyncManager
from backend.core.custom_exceptions import DocumentProcessingError
from backend.rag_solution.data_ingestion.base_processor import BaseProcessor
from backend.rag_solution.data_ingestion.excel_processor import ExcelProcessor
from backend.rag_solution.data_ingestion.pdf_processor import PdfProcessor
from backend.rag_solution.data_ingestion.txt_processor import TxtProcessor
from backend.rag_solution.data_ingestion.word_processor import WordProcessor
from backend.vectordbs.data_types import Document

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class DocumentProcessor:
    """
    Class to process documents based on their file type.

    Attributes:
        processors (Dict[str, BaseProcessor]): A dictionary mapping file extensions to their respective processors.
    """

    def __init__(self, manager: Optional[SyncManager] = None):
        if manager is None:
            manager = multiprocessing.Manager()
        self.manager = manager
        self.processors: Dict[str, BaseProcessor] = {
            ".txt": TxtProcessor(),
            ".pdf": PdfProcessor(self.manager),
            ".docx": WordProcessor(),
            ".xlsx": ExcelProcessor(),
        }

    def process_document(self, file_path: str) -> Iterable[Document]:
        """
        Process a document based on its file extension.

        Args:
            file_path (str): The path to the file to be processed.

        Yields:
            Document: An instance of Document containing the processed data.

        Raises:
            DocumentProcessingError: If there is an error processing the document.
        """
        try:
            file_extension = os.path.splitext(file_path)[1].lower()
            processor = self.processors.get(file_extension)
            if processor:
                return processor.process(file_path)
        except Exception as e:
            logger.error(f"Error processing document {file_path}: {e}", exc_info=True)
            raise DocumentProcessingError(f"Error processing document {file_path}") from e
    
    def extract_metadata_from_processor(self, file_path: str) -> Dict[str, Any]:
        file_extension = os.path.splitext(file_path)[1].lower()
        processor = self.processors.get(file_extension)
        if processor:
            return processor.extract_metadata(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
