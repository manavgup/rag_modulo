# project_root/backend/database/__init__.py

from backend.rag_solution.file_management.database import Base, engine

Base.metadata.create_all(bind=engine)
