import pytest

from exceptions import DocumentProcessingError
from rag_solution.data_ingestion.pdf_processor import PdfProcessor
from vectordbs.data_types import Document


@pytest.mark.asyncio
async def test_process_pdf(test_pdf_path):
    processor = PdfProcessor()
    docs = []
    async for document in processor.process(test_pdf_path):
        docs.append(document)

    assert len(docs) > 0
    assert all(isinstance(doc, Document) for doc in docs)
    assert docs[0].name == str(test_pdf_path)
    assert len(docs[0].chunks) > 0


@pytest.mark.asyncio
async def test_process_pdf_error(test_non_existent_pdf_path):
    processor = PdfProcessor()
    with pytest.raises(DocumentProcessingError):
        async for _ in processor.process(test_non_existent_pdf_path):
            pass
