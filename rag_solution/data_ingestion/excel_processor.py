from typing import AsyncIterable
from vectordbs.data_types import Document
import os
import uuid
import logging
import pandas as pd
from .base_processor import BaseProcessor
from exceptions import DocumentProcessingError
from rag_solution.doc_utils import get_document

logger = logging.getLogger(__name__)

class ExcelProcessor(BaseProcessor):
    async def process(self, file_path: str) -> AsyncIterable[Document]:
        try:
            sheets_data = pd.read_excel(file_path, sheet_name=None)
            full_text = []

            for sheet_name, df in sheets_data.items():
                full_text.append(f"Sheet: {sheet_name}")
                full_text.append(df.to_string(index=False))
                full_text.append("\n")

            text = '\n'.join(full_text)
            chunks = self.chunking_method(text)

            for chunk in chunks:
                yield get_document(name=os.path.basename(file_path),
                                   document_id=str(uuid.uuid4()),
                                   text=chunk)
        except Exception as e:
            logger.error(f"Error reading Excel file {file_path}: {e}", exc_info=True)
            raise DocumentProcessingError(f"Error processing Excel file {file_path}") from e
