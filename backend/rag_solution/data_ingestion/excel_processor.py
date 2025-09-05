import logging
import os
import uuid
from collections.abc import AsyncIterator

import pandas as pd

from core.custom_exceptions import DocumentProcessingError
from rag_solution.data_ingestion.base_processor import BaseProcessor
from rag_solution.doc_utils import get_document
from vectordbs.data_types import Document

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class ExcelProcessor(BaseProcessor):
    """
    Processor for reading and chunking Excel files.

    Methods:
        process(file_path: str) -> AsyncIterable[Document]: Process the Excel file and yield Document instances.
    """

    async def process(self, file_path: str, _document_id: str) -> AsyncIterator[Document]:
        """
        Process the Excel file and yield Document instances.

        Args:
            file_path (str): The path to the Excel file to be processed.
            document_id (str): The ID of the document being processed.

        Yields:
            Document: An instance of Document containing the processed data.

        Raises:
            DocumentProcessingError: If there is an error processing the Excel file.
        """
        try:
            sheets_data = pd.read_excel(file_path, sheet_name=None)
            full_text = []

            for sheet_name, df in sheets_data.items():
                full_text.append(f"Sheet: {sheet_name}")
                full_text.append(df.to_string(index=False))
                full_text.append("\n")

            text = "\n".join(full_text)
            chunks = self.chunking_method(text)

            for chunk in chunks:
                yield get_document(
                    name=os.path.basename(file_path),
                    document_id=str(uuid.uuid4()),
                    text=chunk,
                )
        except Exception as e:
            logger.error(f"Error reading Excel file {file_path}: {e}", exc_info=True)
            raise DocumentProcessingError(
                doc_id=file_path,
                error_type="processing_failed",
                message=f"Error processing Excel file {file_path}",
                details={"error": str(e)},
            ) from e
