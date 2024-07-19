# txt_processor.py
import logging
import os
import uuid
from typing import AsyncIterable

from backend.core.custom_exceptions import DocumentProcessingError
from backend.rag_solution.doc_utils import get_document
from backend.vectordbs.data_types import Document

from .base_processor import BaseProcessor

logger = logging.getLogger(__name__)


class TxtProcessor(BaseProcessor):
    async def process(self, file_path: str) -> AsyncIterable[Document]:
        """
        Process a text file and yield Document objects containing chunks of the text.

        Args:
            file_path (str): The path to the text file.

        Yields:
            Document: Document objects containing chunks of the text file.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
                chunks = self.chunking_method(text)

                for chunk in chunks:
                    yield get_document(
                        name=os.path.basename(file_path),
                        document_id=str(uuid.uuid4()),
                        text=chunk,
                    )
        except Exception as e:
            logger.error(f"Error processing TXT file {file_path}: {e}", exc_info=True)
            raise DocumentProcessingError(
                f"Error processing TXT file {file_path}"
            ) from e
