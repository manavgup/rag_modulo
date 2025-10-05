"""Database management for the RAG Modulo application."""
import logging
import os
from collections.abc import Generator

from core.config import Settings, get_settings
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, declarative_base, sessionmaker

# Configure logging only if not in test environment
if not os.environ.get("PYTEST_CURRENT_TEST"):
    logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not os.environ.get("PYTEST_CURRENT_TEST"):
    logger.info("Database module is being imported")

# Get settings once at module level
settings = get_settings()

# Create database components using settings
# This maintains backward compatibility while enabling dependency injection
engine = create_engine(settings.database_url, echo=not bool(os.environ.get("PYTEST_CURRENT_TEST")))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
if not os.environ.get("PYTEST_CURRENT_TEST"):
    logger.info("Base has been created")


def create_session_factory(db_settings: Settings) -> sessionmaker:
    """Create a sessionmaker with injected settings for dependency injection."""
    db_engine = create_engine(db_settings.database_url, echo=not bool(os.environ.get("PYTEST_CURRENT_TEST")))
    return sessionmaker(autocommit=False, autoflush=False, bind=db_engine)


def get_db() -> Generator[Session, None, None]:
    """
    Create a synchronous database session.

    Yields:
        Session: The database session.
    """
    if not os.environ.get("PYTEST_CURRENT_TEST"):
        logger.info("=== DATABASE DEPENDENCY DEBUG ===")
        logger.info("get_db() called - creating database session")
        logger.info("=== END DATABASE DEPENDENCY DEBUG ===")

    db = SessionLocal()
    try:
        if not os.environ.get("PYTEST_CURRENT_TEST"):
            logger.info("Creating a new database session.")
        yield db
    except SQLAlchemyError as e:
        logger.error("A database error occurred: %s", e, exc_info=True)
        db.rollback()
        raise
    except Exception as e:
        logger.error("An unexpected error occurred: %s", e, exc_info=True)
        raise
    finally:
        db.close()
        if not os.environ.get("PYTEST_CURRENT_TEST"):
            logger.info("Database session closed.")
