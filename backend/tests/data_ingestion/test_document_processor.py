from typing import Any

import pytest

from core.custom_exceptions import DocumentProcessingError
from rag_solution.data_ingestion.document_processor import DocumentProcessor


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fixture_name",
    ["test_txt_path", "test_pdf_path", "test_word_path", "test_excel_path"],
)
@pytest.mark.atomic
async def test_process_document(request: Any, fixture_name: str) -> None:
    test_file = request.getfixturevalue(fixture_name)
    print("*** Fixture name: ", fixture_name)
    processor = DocumentProcessor()
    docs = []
    async for document in processor.process_document(test_file, "test_doc_id"):
        docs.append(document)

    assert len(docs) > 0
    # assert all(isinstance(doc, Document) for doc in docs)
    # assert docs[0].name == str(test_file)
    # assert len(docs[0].chunks) > 0


@pytest.mark.asyncio
async def test_process_document_error(request: Any) -> None:
    test_non_existent_pdf_path = request.getfixturevalue("test_non_existent_pdf_path")
    processor = DocumentProcessor()
    with pytest.raises(DocumentProcessingError):
        async for _ in processor.process_document(test_non_existent_pdf_path, "test_doc_id"):
            pass
