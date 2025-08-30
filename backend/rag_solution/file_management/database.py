# backend/rag_solution/file_management/database.py
import logging
import os

from sqlalchemy import URL, create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from typing import Generator

from core.config import settings

# Configure logging only if not in test environment
if not os.environ.get("PYTEST_CURRENT_TEST"):
    logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not os.environ.get("PYTEST_CURRENT_TEST"):
    logger.info("Database module is being imported")

host = os.environ.get("DB_HOST", settings.collectiondb_host)
if host == "postgres" and os.environ.get("PYTEST_CURRENT_TEST"):
    host = "localhost"

# Synchronous database URL
database_url = URL.create(
    drivername="postgresql",
    username=settings.collectiondb_user,
    password=settings.collectiondb_pass,
    host=settings.collectiondb_host,
    port=settings.collectiondb_port,
    database=settings.collectiondb_name,
)

if not os.environ.get("PYTEST_CURRENT_TEST"):
    logger.debug(f"Database URL: {database_url}")

# Create synchronous engine and session
# Disable SQL echo in test environment
engine = create_engine(database_url, echo=not bool(os.environ.get("PYTEST_CURRENT_TEST")))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
if not os.environ.get("PYTEST_CURRENT_TEST"):
    logger.info("Base has been created")


def get_db() -> Generator[Session, None, None]:
    """
    Create a synchronous database session.

    Yields:
        Session: The database session.
    """
    db = SessionLocal()
    try:
        if not os.environ.get("PYTEST_CURRENT_TEST"):
            logger.info("Creating a new database session.")
        yield db
    except SQLAlchemyError as e:
        logger.error(f"A database error occurred: {e}", exc_info=True)
        db.rollback()
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
    finally:
        db.close()
        if not os.environ.get("PYTEST_CURRENT_TEST"):
            logger.info("Database session closed.")
