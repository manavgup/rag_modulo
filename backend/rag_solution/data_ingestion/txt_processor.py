import logging
import os
import uuid
from typing import Iterable

from backend.core.custom_exceptions import DocumentProcessingError
from backend.rag_solution.data_ingestion.base_processor import BaseProcessor
from backend.rag_solution.doc_utils import get_document
from backend.vectordbs.data_types import Document

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class TxtProcessor(BaseProcessor):
    """
    Processor for reading and chunking text files.

    Methods:
        process(file_path: str) -> Iterable[Document]: Process the text file and yield Document instances.
    """

    def process(self, file_path: str) -> Iterable[Document]:
        """
        Process the text file and yield Document instances.

        Args:
            file_path (str): The path to the text file to be processed.

        Yields:
            Document: An instance of Document containing the processed data.

        Raises:
            DocumentProcessingError: If there is an error processing the text file.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
                chunks = self.chunking_method(text)

                for chunk in chunks:
                    yield get_document(name=os.path.basename(file_path), document_id=str(uuid.uuid4()), text=chunk)
        except Exception as e:
            logger.error(f"Error processing TXT file {file_path}: {e}", exc_info=True)
            raise DocumentProcessingError(f"Error processing TXT file {file_path}") from e
