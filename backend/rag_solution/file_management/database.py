# rag_solution/file_management/database.py
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Synchronous database URL
DATABASE_URL = (
    f"postgresql://{settings.collectiondb_user}:"
    f"{settings.collectiondb_pass}@{settings.collectiondb_host}/"
    f"{settings.collectiondb_name}"
)

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
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
    finally:
        db.close()
        logger.info("Database session closed.")
