# project_root/backend/database/__init__.py

from .database import Base, engine

Base.metadata.create_all(bind=engine)
