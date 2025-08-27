# db.py
"""Database fixtures for pytest."""

from typing import Generator
import pytest
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine
from sqlalchemy import text

from core.logging_utils import get_logger
from rag_solution.file_management.database import Base, engine

logger = get_logger("tests.fixtures.db")

@pytest.fixture(scope="session")
def db_engine() -> Generator[Engine, None, None]:
    """Initialize the database engine for the test session."""
    with engine.connect() as conn:
        try:
            logger.info("Creating tables if they don't exist.")
            Base.metadata.create_all(bind=engine)
            conn.commit()
        except Exception as e:
            logger.error(f"Error during DB setup: {e}")
            raise

    yield engine

@pytest.fixture(scope="function")
def db_session(db_engine: Engine) -> Generator[Session, None, None]:
    """Provide a clean database session for each test."""
    connection = db_engine.connect()
    session = sessionmaker(bind=connection)()
    yield session

    # Clean start for each test
    cleanup_statements = [
        "DELETE FROM user_collection",
        "DELETE FROM user_team",
        "DELETE FROM prompt_templates",
        "DELETE FROM llm_parameters",
        "DELETE FROM files",
        "DELETE FROM suggested_questions",
        "DELETE FROM pipeline_configs",
        "DELETE FROM collections",
        "DELETE FROM teams",
        # do not delete users here
    ]
    
    for stmt in cleanup_statements:
        session.execute(text(stmt))
        
    session.commit()
    session.close()