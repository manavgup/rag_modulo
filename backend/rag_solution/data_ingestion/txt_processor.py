import logging
import os
import uuid
from collections.abc import AsyncIterable

import aiofiles

from core.custom_exceptions import DocumentProcessingError
from rag_solution.data_ingestion.base_processor import BaseProcessor
from rag_solution.doc_utils import get_document
from vectordbs.data_types import Document

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class TxtProcessor(BaseProcessor):
    """
    Processor for reading and chunking text files.

    Methods:
        process(file_path: str) -> AsyncIterable[Document]: Process the text file and yield Document instances.
    """

    async def process(self, file_path: str) -> AsyncIterable[Document]:
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
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                text = await f.read()
                chunks = self.chunking_method(text)

                for chunk in chunks:
                    yield get_document(name=os.path.basename(file_path), document_id=str(uuid.uuid4()), text=chunk)
        except Exception as e:
            logger.error(f"Error processing TXT file {file_path}: {e}", exc_info=True)
            raise DocumentProcessingError(f"Error processing TXT file {file_path}") from e
