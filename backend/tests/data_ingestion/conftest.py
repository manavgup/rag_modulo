import pytest
import pandas as pd
from docx import Document as DocxDocument
import pymupdf


@pytest.fixture
def test_txt_path(tmp_path):
    p = tmp_path / "test.txt"
    p.write_text("This is a simple text file.")
    return str(p)


@pytest.fixture
def test_excel_path(tmp_path):
    p = tmp_path / "test.xlsx"
    df = pd.DataFrame({"col1": [1, 2], "col2": ["A", "B"]})
    df.to_excel(p, index=False, engine="openpyxl")
    return str(p)


@pytest.fixture
def test_word_path(tmp_path):
    p = tmp_path / "test.docx"
    doc = DocxDocument()
    doc.add_paragraph("This is a test Word document.")
    doc.save(p)
    return str(p)


@pytest.fixture
def test_pdf_path(tmp_path):
    p = tmp_path / "test.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "This is a test PDF document.")
    doc.save(p)
    doc.close()
    return str(p)


@pytest.fixture
def test_non_existent_pdf_path(tmp_path):
    return str(tmp_path / "non_existent.pdf")
