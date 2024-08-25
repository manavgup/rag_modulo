from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.rag_solution.file_management.database import get_db
from backend.rag_solution.schemas.file_schema import DocumentDelete, FileOutput, FileMetadata
from backend.rag_solution.services.file_management_service import FileManagementService

router = APIRouter(prefix="/api/files", tags=["files"])

@router.post("/{user_id}/{collection_id}", 
    response_model=FileOutput,
    summary="Upload a file",
    description="Upload a file to a specific collection for a user",
    responses={
        200: {"description": "File uploaded successfully"},
        400: {"description": "Invalid input"},
        404: {"description": "User or collection not found"},
        500: {"description": "Internal server error"}
    }
)
def upload_file(user_id: UUID, collection_id: UUID, file: UploadFile, metadata: Optional[FileMetadata] = None, db: Session = Depends(get_db)):
    """
    Upload a file to a specific collection for a user.

    Args:
        user_id (UUID): The ID of the user uploading the file.
        collection_id (UUID): The ID of the collection to upload the file to.
        file (UploadFile): The file to be uploaded.
        db (Session): The database session.

    Returns:
        FileOutput: The uploaded file information.
    """
    _file_service = FileManagementService(db)
    return _file_service.upload_and_create_file_record(file, user_id, collection_id, metadata)

@router.get("/{user_id}/{collection_id}", 
    response_model=List[str],
    summary="Get collection files",
    description="Get a list of files in a specific collection for a user",
    responses={
        200: {"description": "Files retrieved successfully"},
        404: {"description": "User or collection not found"},
        500: {"description": "Internal server error"}
    }
)
def get_collection_files(user_id: UUID, collection_id: UUID, db: Session = Depends(get_db)):
    """
    Get a list of files in a specific collection for a user.

    Args:
        user_id (UUID): The ID of the user.
        collection_id (UUID): The ID of the collection.
        db (Session): The database session.

    Returns:
        List[str]: A list of filenames in the collection.
    """
    _file_service = FileManagementService(db)
    return _file_service.get_files(user_id, collection_id)

@router.get("/{user_id}/{collection_id}/{filename}",
    summary="Get file path",
    description="Get the file path for a specific file in a collection",
    responses={
        200: {"description": "File path retrieved successfully"},
        404: {"description": "File not found"},
        500: {"description": "Internal server error"}
    }
)
def get_file_path(user_id: UUID, collection_id: UUID, filename: str, db: Session = Depends(get_db)):
    """
    Get the file path for a specific file in a collection.

    Args:
        user_id (UUID): The ID of the user.
        collection_id (UUID): The ID of the collection.
        filename (str): The name of the file.
        db (Session): The database session.

    Returns:
        dict: A dictionary containing the file path.

    Raises:
        HTTPException: If the file is not found.
    """
    _file_service = FileManagementService(db)
    file_path = _file_service.get_file_path(user_id, collection_id, filename)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return {"file_path": str(file_path)}

@router.delete("/", 
    response_model=bool,
    summary="Delete files",
    description="Delete files from a collection",
    responses={
        200: {"description": "Files deleted successfully"},
        400: {"description": "Invalid input"},
        404: {"description": "Files not found"},
        500: {"description": "Internal server error"}
    }
)
def delete_files(doc_delete: DocumentDelete, db: Session = Depends(get_db)):
    """
    Delete files from a collection.

    Args:
        doc_delete (DocumentDelete): The document delete request containing user_id, collection_id, and filenames.
        db (Session): The database session.

    Returns:
        bool: True if the files were successfully deleted, False otherwise.
    """
    _file_service = FileManagementService(db)
    return _file_service.delete_files(doc_delete.user_id, doc_delete.collection_id, doc_delete.filenames)

@router.put("/{file_id}/metadata", 
    response_model=FileOutput,
    summary="Update file metadata",
    description="Update the metadata of a specific file",
    responses={
        200: {"description": "File metadata updated successfully"},
        404: {"description": "File not found"},
        500: {"description": "Internal server error"}
    }
)
def update_file_metadata(file_id: UUID, metadata: FileMetadata, db: Session = Depends(get_db)):
    _file_service = FileManagementService(db)
    return _file_service.update_file_metadata(file_id, metadata)