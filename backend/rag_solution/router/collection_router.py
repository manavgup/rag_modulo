from uuid import UUID
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, UploadFile, Form, File, Request, HTTPException
from sqlalchemy.orm import Session

from rag_solution.file_management.database import get_db
from rag_solution.schemas.collection_schema import CollectionInput, CollectionOutput
from rag_solution.schemas.user_schema import UserInput
from rag_solution.services.user_service import UserService
from rag_solution.services.collection_service import CollectionService
from rag_solution.services.file_management_service import FileManagementService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/collections",
    tags=["collections"]
)

@router.post("/create", 
    summary="Create a new collection", 
    response_model=CollectionOutput,
    description="Create a new collection with the provided input data.",
    responses={
        200: {"description": "Collection created successfully"},
        400: {"description": "Invalid input data"},
        500: {"description": "Internal server error"}
    }
)
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

@router.post("/create__with_documents", 
    summary="Create a new collection with documents", 
    response_model=CollectionOutput,
    description="Create a new collection and upload documents to it.",
    responses={
        200: {"description": "Collection created with documents successfully"},
        400: {"description": "Invalid input data"},
        500: {"description": "Internal server error"}
    }
)
def create_collection_with_documents(
    request: Request,
    collection_name: str = Form(...),
    is_private: bool = Form(...),
    user_id: UUID = Form(...),
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

    if not hasattr(request.state, 'user') or request.state.user['uuid'] != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized to access this resource")

    try:
        collection_service = CollectionService(db)
        collection = collection_service.create_collection_with_documents(
            collection_name,
            is_private,
            user_id,
            files,
            background_tasks
        )
        logger.info(f"Collection created successfully: {collection.id}")
        return collection
    except Exception as e:
        logger.error(f"Error creating collection: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{collection_name}", 
    summary="Retrieve a collection by name", 
    response_model=CollectionOutput,
    description="Retrieve a collection using its name.",
    responses={
        200: {"description": "Collection retrieved successfully"},
        404: {"description": "Collection not found"},
        500: {"description": "Internal server error"}
    }
)
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

@router.delete("/{collection_name}", 
    summary="Delete a collection", 
    response_model=bool,
    description="Delete a collection using its name.",
    responses={
        200: {"description": "Collection deleted successfully"},
        404: {"description": "Collection not found"},
        500: {"description": "Internal server error"}
    }
)
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