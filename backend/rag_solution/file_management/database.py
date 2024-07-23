# rag_solution/file_management/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from core.config import settings

# DATABASE_URL = "postgresql://user:password@localhost/dbname"
DATABASE_URL = (
    f"postgresql://{settings.collectiondb_user}:"
    f"{settings.collectiondb_pass}@{settings.collectiondb_host}/"
    f"{settings.collectiondb_name}"
)
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine)
Base = declarative_base()

# Dependency to get DB session
def get_db():
    """
    Create a database session.
    Yields:
        Session: The database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
