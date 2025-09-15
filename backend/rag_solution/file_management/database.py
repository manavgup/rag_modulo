# backend/rag_solution/file_management/database.py
import logging
import os
from collections.abc import Generator

from core.config import Settings, get_settings
from sqlalchemy import URL, create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, declarative_base, sessionmaker

# Configure logging only if not in test environment
if not os.environ.get("PYTEST_CURRENT_TEST"):
    logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not os.environ.get("PYTEST_CURRENT_TEST"):
    logger.info("Database module is being imported")


# Initialize database components with dependency injection
def create_database_url(settings: Settings | None = None) -> URL:
    """Create database URL from settings."""
    if settings is None:
        settings = get_settings()

    host = os.environ.get("DB_HOST", settings.collectiondb_host)
    if host == "postgres" and os.environ.get("PYTEST_CURRENT_TEST"):
        host = "localhost"

    database_url = URL.create(
        drivername="postgresql",
        username=settings.collectiondb_user,
        password=settings.collectiondb_pass,
        host=host,  # Use the adjusted host
        port=settings.collectiondb_port,
        database=settings.collectiondb_name,
    )

    if not os.environ.get("PYTEST_CURRENT_TEST"):
        logger.debug(f"Database URL: {database_url}")

    return database_url


# Create database components using default settings
# This maintains backward compatibility while enabling dependency injection
_default_database_url = create_database_url()
engine = create_engine(_default_database_url, echo=not bool(os.environ.get("PYTEST_CURRENT_TEST")))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
if not os.environ.get("PYTEST_CURRENT_TEST"):
    logger.info("Base has been created")


def create_session_factory(settings: Settings | None = None) -> sessionmaker[Session]:
    """Create a sessionmaker with injected settings for dependency injection."""
    if settings is None:
        settings = get_settings()

    database_url = create_database_url(settings)
    engine = create_engine(database_url, echo=not bool(os.environ.get("PYTEST_CURRENT_TEST")))
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


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
        logger.error(f"A database error occurred: {e}", exc_info=True)
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        raise
    finally:
        db.close()
        if not os.environ.get("PYTEST_CURRENT_TEST"):
            logger.info("Database session closed.")
