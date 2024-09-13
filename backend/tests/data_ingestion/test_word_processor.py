import os

import pytest

from backend.core.custom_exceptions import DocumentProcessingError
from backend.rag_solution.data_ingestion.word_processor import WordProcessor
from backend.vectordbs.data_types import Document


@pytest.mark.asyncio
async def test_process_word(test_word_path):
    processor = WordProcessor()
    docs = []
    async for document in processor.process(test_word_path):
        docs.append(document)

    assert len(docs) > 0
    assert all(isinstance(doc, Document) for doc in docs)
    assert docs[0].name == os.path.basename(str(test_word_path))
    assert len(docs[0].chunks) > 0


@pytest.mark.asyncio
async def test_process_word_error(test_non_existent_pdf_path):
    processor = WordProcessor()
    with pytest.raises(DocumentProcessingError):
        async for _ in processor.process(test_non_existent_pdf_path):
            pass
