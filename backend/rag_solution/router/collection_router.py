import uuid
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, UploadFile, Form, File
from sqlalchemy.orm import Session

from backend.rag_solution.file_management.database import get_db
from backend.rag_solution.schemas.collection_schema import CollectionInput, CollectionOutput
from backend.rag_solution.schemas.user_schema import UserInput
from backend.rag_solution.services.user_service import UserService
from backend.rag_solution.services.collection_service import CollectionService
from backend.rag_solution.services.file_management_service import \
    FileManagementService

router = APIRouter(
    prefix="/api/collections",
    tags=["collections"]
)

@router.post("/create", summary="Create a new collection", response_model=CollectionOutput)
def create_collection(collection_input: CollectionInput, db: Session = Depends(get_db)):
    """
    Create a new collection.

    Args:
        collection_input (CollectionInput): The input data for creating a collection.
        db (Session): The database session.

    Returns:
        CollectionOutput: The created collection.
    """
    _service = CollectionService(db, FileManagementService(db))
    return _service.create_collection(db, collection_input)

@router.post("/create__with_documents", summary="Create a new collection with documents", response_model=CollectionOutput)
def create_collection_with_documents(
    collection_name: str = Form(...),
    is_private: bool = Form(...),
    files: List[UploadFile] = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
):
    """
    Create a new collection with documents.

    Args:
        collection_name (str): The name of the collection.
        is_private (bool): Whether the collection is private.
        user_id (uuid.UUID): The ID of the user creating the collection.
        files (List[UploadFile]): The list of files to be added to the collection.
        background_tasks (BackgroundTasks): Background tasks for processing.
        db (Session): The database session.

    Returns:
        CollectionOutput: The created collection with documents.
    """
    # HACKY - TO BE REMOVED
    user = UserService(db).create_user(UserInput(ibm_id="test_ibm_id", email="test@example.com", name="Test User"))
    # HACKY - TO BE REMOVED 

    _service = CollectionService(db)
    return _service.create_collection_with_documents(collection_name, is_private, user.id, files, background_tasks)

@router.get("/{collection_name}", summary="Retrieve a collection by name", response_model=CollectionOutput)
def get_collection(collection_name: str, db: Session = Depends(get_db)):
    """
    Retrieve a collection by name.

    Args:
        collection_name (str): The name of the collection to retrieve.
        db (Session): The database session.

    Returns:
        CollectionOutput: The retrieved collection.
    """
    _service = CollectionService(db, FileManagementService(db))
    return _service.get_collection(collection_name)

@router.delete("/{collection_name}", summary="Delete a collection", response_model=bool)
def delete_collection(collection_name: str, db: Session = Depends(get_db)):
    """
    Delete a collection by name.

    Args:
        collection_name (str): The name of the collection to delete.
        db (Session): The database session.

    Returns:
        bool: True if the collection was successfully deleted, False otherwise.
    """
    _service = CollectionService(db, FileManagementService(db))
    return _service.delete_collection(collection_name)