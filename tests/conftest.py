import pytest
import pymupdf
from config import settings
from elasticsearch import Elasticsearch
from pymilvus import connections
import pinecone
import weaviate
import chromadb

@pytest.fixture(scope="session")
def vector_store_config():
    return {
        "vector_db": settings.vector_db,
        "collection_name": settings.collection_name,
        "embedding_model": settings.embedding_model,
        "embedding_dim": settings.embedding_dim,
        "upsert_batch_size": settings.upsert_batch_size,
    }

@pytest.fixture(scope="session")
def vector_store_client(vector_store_config):
    vector_db = vector_store_config["vector_db"]

    if vector_db == "elasticsearch":
        client = Elasticsearch(
            [f"{settings.elastic_host}:{settings.elastic_port}"],
            ca_certs=settings.elastic_cacert_path,
            basic_auth=("elastic", settings.elastic_password)
        )
    elif vector_db == "milvus":
        connections.connect(
            alias="default",
            host=settings.milvus_host,
            port=settings.milvus_port,
            user=settings.milvus_user,
            password=settings.milvus_password
        )
        client = None  # Milvus uses a global connection
    elif vector_db == "pinecone":
        pinecone.init(
            api_key=settings.pinecone_api_key,
            environment=settings.pinecone_region
        )
        client = pinecone.Index(settings.collection_name)
    elif vector_db == "weaviate":
        client = weaviate.Client(
            url=f"http://{settings.weaviate_host}:{settings.weaviate_port}",
            auth_client_secret=weaviate.AuthClientPassword(
                username=settings.weaviate_username,
                password=settings.weaviate_password
            )
        )
    elif vector_db == "chroma":
        client = chromadb.Client(
            settings=chromadb.config.Settings(
                chroma_api_impl="rest",
                chroma_server_host=settings.chromadb_host,
                chroma_server_http_port=settings.chromadb_port
            )
        )
    else:
        pytest.skip(f"Unsupported vector store: {vector_db}")

    yield client

    # Cleanup
    if vector_db == "elasticsearch":
        client.close()
    elif vector_db == "milvus":
        connections.disconnect("default")
    elif vector_db == "pinecone":
        pinecone.deinit()

# Existing fixtures
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