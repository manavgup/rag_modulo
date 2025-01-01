"""Pytest configuration and shared fixtures."""

import asyncio
import uuid
import logging
import os
import pytest
from sqlalchemy.orm import scoped_session, sessionmaker

from core.config import settings
from rag_solution.file_management.database import Base, engine
from vectordbs.factory import get_datastore
from vectordbs.error_types import CollectionError
from rag_solution.models.collection import Collection
from rag_solution.models.file import File
from rag_solution.models.team import Team
from rag_solution.models.user import User
from rag_solution.models.user_collection import UserCollection
from rag_solution.models.user_team import UserTeam
from rag_solution.models.provider_config import ProviderModelConfig
from rag_solution.models.llm_parameters import LLMParameters
from rag_solution.models.prompt_template import PromptTemplate

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@pytest.fixture(scope="session")
def db_engine():
    """Create a synchronous engine for the database session."""
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

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
    db_session.query(ProviderModelConfig).delete()
    db_session.query(LLMParameters).delete()
    db_session.query(PromptTemplate).delete()
    db_session.commit()

@pytest.fixture(autouse=True)
def db_session_rollback(db_session):
    """Rollback database changes after each test."""
    yield
    db_session.rollback()

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

def pytest_configure(config):
    """Configure pytest markers for different vector databases."""
    for db in ["chromadb", "milvus", "weaviate", "pinecone", "elasticsearch"]:
        config.addinivalue_line(
            "markers", f"{db}: mark test to run only on {db.capitalize()}"
        )

def pytest_collection_modifyitems(config, items):
    """Modify test items based on configured vector database."""
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

@pytest.fixture(autouse=True)
def env_setup():
    """Set up environment variables for testing."""
    os.environ['RAG_LLM'] = 'watsonx'
    os.environ['JWT_SECRET_KEY'] = 'test_secret_key'
    yield
