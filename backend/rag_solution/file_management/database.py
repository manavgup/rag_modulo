# rag_solution/file_management/database.py
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from backend.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Synchronous database URL
DATABASE_URL = (
    f"postgresql://{settings.collectiondb_user}:{settings.collectiondb_pass}@{settings.collectiondb_host}:{settings.collectiondb_port}/{settings.collectiondb_name}"
)

logger.debug(f"Database URL: {DATABASE_URL}")

# Create synchronous engine and session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """
    Create a synchronous database session.

    Yields:
        Session: The database session.
    """
    db = SessionLocal()
    try:
        logger.info("Creating a new database session.")
        yield db
    except SQLAlchemyError as e:
        logger.error(f"A database error occurred: {e}", exc_info=True)
        db.rollback()
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
    finally:
        db.close()
        logger.info("Database session closed.")
