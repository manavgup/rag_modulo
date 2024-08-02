from fastapi import APIRouter, Depends, UploadFile, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import uuid

from rag_solution.schemas.collection_schema import CollectionInput, CollectionOutput
from rag_solution.services.collection_service import CollectionService
from rag_solution.services.file_management_service import FileManagementService
from rag_solution.file_management.database import get_db

router = APIRouter(
    prefix="/api/collections",
    tags=["collections"]
)

@router.post("/create", summary="Create a new collection", response_model=CollectionOutput)
def create_collection(collection_input: CollectionInput, db: Session = Depends(get_db)):
    _service = CollectionService(db, FileManagementService(db))
    return _service.create_collection(db, collection_input)

@router.post("/create__with_documents", summary="Create a new collection with documents", response_model=CollectionOutput)
def create_collection_with_documents(
    collection_name: str,
    is_private: bool,
    user_id: uuid.UUID,
    files: List[UploadFile],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    _service = CollectionService(db, FileManagementService(db))
    return _service.create_collection_with_documents(db, collection_name, is_private, user_id, files, background_tasks)

@router.get("/{collection_name}", summary="Retrieve a collection by name", response_model=CollectionOutput)
def get_collection(collection_name: str, db: Session = Depends(get_db)):
    _service = CollectionService(db, FileManagementService(db))
    return _service.get_collection(collection_name)

@router.delete("/{collection_name}", summary="Delete a collection", response_model=bool)
def delete_collection(collection_name: str, db: Session = Depends(get_db)):
    _service = CollectionService(db, FileManagementService(db))
    return _service.delete_collection(collection_name)
