import logging
import os
import uuid
from typing import AsyncIterable

from docx import Document as DocxDocument

from exceptions import DocumentProcessingError
from rag_solution.doc_utils import get_document
from vectordbs.data_types import Document

from .base_processor import BaseProcessor

logger = logging.getLogger(__name__)


class WordProcessor(BaseProcessor):
    async def process(self, file_path: str) -> AsyncIterable[Document]:
        try:
            doc = DocxDocument(file_path)
            full_text = []

            for paragraph in doc.paragraphs:
                full_text.append(paragraph.text)

            text = "\n".join(full_text)
            chunks = self.chunking_method(text)

            for chunk in chunks:
                yield get_document(
                    name=os.path.basename(file_path),
                    document_id=str(uuid.uuid4()),
                    text=chunk,
                )
        except Exception as e:
            logger.error(f"Error reading Word file {file_path}: {e}", exc_info=True)
            raise DocumentProcessingError(
                f"Error processing Word file {file_path}"
            ) from e
