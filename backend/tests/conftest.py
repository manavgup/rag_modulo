import asyncio
import uuid

import chromadb
import pymupdf
import pytest
import weaviate
from core.config import settings
from elasticsearch import Elasticsearch
from vectordbs.milvus_store import MilvusStore
from fastapi.testclient import TestClient
from pinecone import Pinecone
from pymilvus import connections
from rag_solution.file_management.database import DATABASE_URL, engine as sync_engine, Base, SessionLocal
# Remove or comment out these lines:
from rag_solution.models.collection import Collection
from rag_solution.models.file import File
from rag_solution.models.team import Team
# Import all models to ensure they're registered with SQLAlchemy
from rag_solution.models.user import User
from rag_solution.models.user_collection import UserCollection
from rag_solution.models.user_team import UserTeam
from rag_solution.schemas.user_schema import UserInput
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from vectordbs.vector_store import VectorStore
import logging
from vectordbs.factory import get_datastore
from vectordbs.error_types import CollectionError
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


#from main import app

# DATABASE_URL = (
#     f"postgresql://{settings.collectiondb_user}:{settings.collectiondb_pass}@{settings.collectiondb_host}:{settings.collectiondb_port}/{settings.collectiondb_name}"
# )
# # Use synchronous database URL

# print (f"**DATABASE URL: {DATABASE_URL}")
# sync_engine = create_engine(DATABASE_URL)
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

@pytest.fixture(scope="session")
def db_engine():
    """Create a synchronous engine for the database session."""
    Base.metadata.create_all(bind=sync_engine)
    yield sync_engine
    Base.metadata.drop_all(bind=sync_engine)

@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create a new database session for a test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session_factory = sessionmaker(bind=connection)
    session = scoped_session(session_factory)

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(autouse=True)
def clean_db(db_session):
    """Clean up the database before each test."""
    # Delete in the correct order to avoid foreign key violations
    db_session.query(UserCollection).delete()
    db_session.query(UserTeam).delete()
    db_session.query(File).delete()
    db_session.query(Collection).delete()
    db_session.query(Team).delete()
    db_session.query(User).delete()
    db_session.commit()

@pytest.fixture(autouse=True)
def db_session_rollback(db_session):
    yield
    db_session.rollback()

def pytest_configure(config):
    for db in ["chromadb", "milvus", "weaviate", "pinecone", "elasticsearch"]:
        config.addinivalue_line(
            "markers", f"{db}: mark test to run only on {db.capitalize()}"
        )

def pytest_collection_modifyitems(config, items):
    selected_vector_db = settings.vector_db.strip().lower()
    skip_markers = {
        "chromadb": "chroma",
        "milvus": "milvus",
        "weaviate": "weaviate",
        "pinecone": "pinecone",
        "elasticsearch": "elasticsearch",
    }
    skip_marker = pytest.mark.skip(reason=f"skipped due to {selected_vector_db} configuration")
    
    for item in items:
        for db, marker in skip_markers.items():
            if db != selected_vector_db and marker in item.keywords:
                item.add_marker(skip_marker)

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
def vector_store_client():
    vector_db = settings.vector_db
    try:
        logger.debug(f"Initializing {vector_db} client")
        if vector_db == "milvus":
            settings.milvus_host = "localhost"
            settings.milvus_port = "19530"

        client = get_datastore(vector_db)
        logger.debug(f"Vector store client initialized: {client}")
        yield client
    except Exception as e:
        pytest.skip(f"Failed to initialize {vector_db} client: {str(e)}")
    finally:
        if hasattr(client, 'close'):
            client.close()

@pytest.fixture
def user_input():
    return UserInput(
        ibm_id=str(uuid.uuid4()),
        email="test@example.com",
        name="Test User"
    )

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
    return "tests/test_files/non_existent.pdf"

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