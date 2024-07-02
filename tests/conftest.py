import pytest
import pymupdf
from config import settings

@pytest.fixture(scope="module")
def test_pdf_path(tmp_path_factory):
    test_file = tmp_path_factory.mktemp("data") / "test.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((100, 100), "This is a test document.")
    doc.save(test_file)
    doc.close()
    return test_file

@pytest.fixture(scope="module")
def test_non_existent_pdf_path():
    return 'tests/test_files/non_existent.pdf'

@pytest.fixture(scope="module")
def test_txt_path(tmp_path_factory):
    test_file = tmp_path_factory.mktemp("data") / "test.txt"
    test_file.write_text("This is a test text file.")
    return test_file

@pytest.fixture(scope="module")
def test_word_path(tmp_path_factory):
    test_file = tmp_path_factory.mktemp("data") / "test.docx"
    from docx import Document
    doc = Document()
    doc.add_paragraph("This is a test Word document.")
    doc.save(test_file)
    return test_file

@pytest.fixture(scope="module")
def test_excel_path(tmp_path_factory):
    test_file = tmp_path_factory.mktemp("data") / "test.xlsx"
    import pandas as pd
    df = pd.DataFrame({"Column1": ["Row1", "Row2"], "Column2": ["Data1", "Data2"]})
    df.to_excel(test_file, index=False)
    return test_file
