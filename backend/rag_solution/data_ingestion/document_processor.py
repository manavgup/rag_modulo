import logging
import os
from typing import Iterable, Dict

from core.custom_exceptions import DocumentProcessingError
from vectordbs.data_types import Document

from .base_processor import BaseProcessor
from .excel_processor import ExcelProcessor
from .pdf_processor import PdfProcessor
from .txt_processor import TxtProcessor
from .word_processor import WordProcessor

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class DocumentProcessor:
    """
    Class to process documents based on their file type.

    Attributes:
        processors (Dict[str, BaseProcessor]): A dictionary mapping file extensions to their respective processors.
    """

    def __init__(self) -> None:
        super().__init__()
        self.processors: Dict[str, BaseProcessor] = {
            ".txt": TxtProcessor(),
            ".pdf": PdfProcessor(),
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
                for doc in processor.process(file_path):
                    yield doc
            else:
                logger.warning(f"Unsupported file type: {file_extension}")
        except Exception as e:
            logger.error(f"Error processing document {file_path}: {e}", exc_info=True)
            raise DocumentProcessingError(f"Error processing document {file_path}") from e
