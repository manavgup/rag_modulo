import pytest

from backend.core.custom_exceptions import DocumentProcessingError
from backend.rag_solution.data_ingestion.txt_processor import TxtProcessor
from backend.vectordbs.data_types import Document


@pytest.mark.asyncio
async def test_process_txt(test_txt_path):
    processor = TxtProcessor()
    docs = []
    async for document in processor.process(test_txt_path):
        docs.append(document)

    assert len(docs) > 0
    assert all(isinstance(doc, Document) for doc in docs)
    assert docs[0].name == str(test_txt_path)
    assert len(docs[0].chunks) > 0


@pytest.mark.asyncio
async def test_process_txt_error(test_non_existent_pdf_path):
    processor = TxtProcessor()
    with pytest.raises(DocumentProcessingError):
        async for _ in processor.process(test_non_existent_pdf_path):
            pass
