# document_processor.py
import logging
import os
from typing import AsyncIterable, Dict

from error_handling import async_error_handler
from exceptions import DocumentProcessingError
from vectordbs.data_types import Document

from .base_processor import BaseProcessor
from .excel_processor import ExcelProcessor
from .pdf_processor import PdfProcessor
from .txt_processor import TxtProcessor
from .word_processor import WordProcessor

logger = logging.getLogger(__name__)


class DocumentProcessor:
    def __init__(self) -> None:
        super().__init__()
        self.processors: Dict[str, BaseProcessor] = {
            ".txt": TxtProcessor(),
            ".pdf": PdfProcessor(),
            ".docx": WordProcessor(),
            ".xlsx": ExcelProcessor(),
        }

    @async_error_handler
    async def process_document(self, file_path: str) -> AsyncIterable[Document]:
        try:
            file_extension = os.path.splitext(file_path)[1].lower()
            processor = self.processors.get(file_extension)
            if processor:
                async for doc in processor.process(file_path):
                    yield doc
            else:
                logger.warning(f"Unsupported file type: {file_extension}")
        except Exception as e:
            logger.error(f"Error processing document {file_path}: {e}", exc_info=True)
            raise DocumentProcessingError(
                f"Error processing document {file_path}"
            ) from e
