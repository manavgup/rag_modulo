from uuid import UUID
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, UploadFile, Form, File, Request, HTTPException
from sqlalchemy.orm import Session

from rag_solution.file_management.database import get_db
from rag_solution.schemas.collection_schema import CollectionInput, CollectionOutput
from rag_solution.schemas.user_schema import UserInput
from rag_solution.services.user_service import UserService
from rag_solution.services.user_collection_service import UserCollectionService
from rag_solution.schemas.user_collection_schema import UserCollectionOutput
from rag_solution.services.collection_service import CollectionService
from rag_solution.services.file_management_service import FileManagementService
from rag_solution.schemas.file_schema import DocumentDelete, FileOutput, FileMetadata
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/collections",
    tags=["collections"]
)

@router.post("", 
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

@router.post("/with-files", 
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

@router.get("/{collection_id}", 
    summary="Retrieve a collection by id.", 
    response_model=CollectionOutput,
    description="Retrieve a collection by it's unique id.",
    responses={
        200: {"description": "Collection retrieved successfully"},
        404: {"description": "Collection not found"},
        500: {"description": "Internal server error"}
    }
)
def get_collection(collection_id: UUID, db: Session = Depends(get_db)):
    """
    Retrieve a collection by id.

    Args:
        collection_id (UUID): The ID of the collection to retrieve.
        db (Session): The database session.

    Returns:
        CollectionOutput: The retrieved collection.
    """
    _service = CollectionService(db, FileManagementService(db))
    return _service.get_collection(collection_id)

@router.delete("/{collection_id}", 
    summary="Delete a collection by id.", 
    description="Delete a collection by it's unique id.",
    responses={
        204: {"description": "No content on successful collection deletion"},
        404: {"description": "Collection not found"},
        500: {"description": "Internal server error"}
    }
)
def delete_collection(collection_id: UUID, db: Session = Depends(get_db)):
    """
    Delete a collection by id.

    Args:
        collection_id (UUID): The ID of the collection to delete.
        db (Session): The database session.

    Returns:
        bool: True if the collection was successfully deleted, False otherwise.
    """
    _service = CollectionService(db, FileManagementService(db))
    _service.delete_collection(collection_id)

@router.get("/{collection_id}/users", 
    response_model=List[UserCollectionOutput],
    summary="Get collection users",
    description="Get all users associated with a collection",
    responses={
        200: {"description": "Successfully retrieved collection users"},
        404: {"description": "Collection not found"},
        500: {"description": "Internal server error"}
    }
)
def get_collection_users(collection_id: UUID, db: Session = Depends(get_db)):
    service = UserCollectionService(db)
    return service.get_collection_users(collection_id)

@router.delete("/{collection_id}/users", 
    summary="Remove all users from collection",
    description="Remove all users from a specific collection",
    responses={
        204: {"description": "No content in case all users successfully removed from collection"},
        404: {"description": "Collection not found"},
        500: {"description": "Internal server error"}
    }
)
def remove_all_users_from_collection(collection_id: UUID, db: Session = Depends(get_db)):
    service = UserCollectionService(db)
    service.remove_all_users_from_collection(collection_id)

@router.get("/{collection_id}/files", 
    response_model=List[str],
    summary="Get collection files",
    description="Get a list of files in a specific collection for a user",
    responses={
        200: {"description": "Files retrieved successfully"},
        404: {"description": "User or collection not found"},
        500: {"description": "Internal server error"}
    }
)
def get_collection_files(collection_id: UUID, db: Session = Depends(get_db)):
    """
    Get a list of files in a specific collection.

    Args:
        collection_id (UUID): The ID of the collection.
        db (Session): The database session.

    Returns:
        List[str]: A list of filenames in the collection.
    """
    _file_service = FileManagementService(db)
    return _file_service.get_files(collection_id)

@router.get("/{collection_id}/files/{filename}",
    summary="Get file path",
    description="Get the file path for a specific file in a collection",
    responses={
        200: {"description": "File path retrieved successfully"},
        404: {"description": "File not found"},
        500: {"description": "Internal server error"}
    }
)
def get_file_path(collection_id: UUID, filename: str, db: Session = Depends(get_db)):
    """
    Get the file path for a specific file in a collection.

    Args:
        collection_id (UUID): The ID of the collection.
        filename (str): The name of the file.
        db (Session): The database session.

    Returns:
        dict: A dictionary containing the file path.

    Raises:
        HTTPException: If the file is not found.
    """
    _file_service = FileManagementService(db)
    file_path = _file_service.get_file_path(collection_id, filename)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return {"file_path": str(file_path)}

@router.delete("/{collection_id}/files", 
    summary="Delete files",
    description="Delete files from a collection",
    responses={
        204: {"description": "No content if files deleted successfully"},
        400: {"description": "Invalid input"},
        404: {"description": "Files not found"},
        500: {"description": "Internal server error"}
    }
)
def delete_files(collection_id: UUID, doc_delete: DocumentDelete, db: Session = Depends(get_db)):
    """
    Delete files from a collection.

    Args:
        doc_delete (DocumentDelete): The document delete request containing list of filenames.
        db (Session): The database session.
    """
    _file_service = FileManagementService(db)
    _file_service.delete_files(collection_id, doc_delete.filenames)

@router.put("/{collection_id}/files/{file_id}/metadata", 
    response_model=FileOutput,
    summary="Update file metadata",
    description="Update the metadata of a specific file",
    responses={
        200: {"description": "File metadata updated successfully"},
        404: {"description": "File not found"},
        500: {"description": "Internal server error"}
    }
)
def update_file_metadata(collection_id: UUID, file_id: UUID, metadata: FileMetadata, db: Session = Depends(get_db)):
    _file_service = FileManagementService(db)
    return _file_service.update_file_metadata(collection_id, file_id, metadata)