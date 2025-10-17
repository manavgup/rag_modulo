"""File management routes."""

import logging
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile
from pydantic import UUID4
from sqlalchemy.orm import Session

from core.config import Settings, get_settings
from rag_solution.core.dependencies import verify_user_access
from rag_solution.file_management.database import get_db
from rag_solution.schemas.file_schema import FileOutput
from rag_solution.schemas.user_schema import UserOutput
from rag_solution.services.collection_service import CollectionService
from rag_solution.services.file_management_service import FileManagementService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/{user_id}/files",
    response_model=FileOutput,
    summary="Upload a file",
    description="Upload a file to a user's collection",
    responses={
        201: {"description": "File uploaded successfully"},
        400: {"description": "Invalid file or input data"},
        403: {"description": "Not authorized"},
        500: {"description": "Internal server error"},
    },
)
async def upload_file(
    user_id: UUID4,
    file: UploadFile,
    collection_id: UUID4,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[UserOutput, Depends(verify_user_access)],
    settings: Annotated[Settings, Depends(get_settings)],
    background_tasks: BackgroundTasks,
) -> FileOutput:
    """Upload a file to a user's collection and trigger document processing."""
    collection_service = CollectionService(db, settings)
    try:
        # Use the service method that handles both upload and processing
        return collection_service.upload_file_and_process(file, user_id, collection_id, background_tasks)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to upload file: {e!s}") from e


@router.delete(
    "/{user_id}/files/{file_id}",
    response_model=bool,
    summary="Delete a file",
    description="Delete a file from a user's collection",
    responses={
        200: {"description": "File deleted successfully"},
        403: {"description": "Not authorized"},
        404: {"description": "File not found"},
        500: {"description": "Internal server error"},
    },
)
async def delete_file(
    user_id: UUID4,
    file_id: UUID4,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[UserOutput, Depends(verify_user_access)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> bool:
    """Delete a file from a user's collection.

    SECURITY: Verifies user has access to the file's collection before deletion.
    """
    service = FileManagementService(db, settings)
    try:
        # SECURITY FIX: Verify user has access to the file's collection
        file = service.get_file_by_id(file_id)

        # Import UserCollectionService for authorization check
        from rag_solution.services.user_collection_service import UserCollectionService

        user_collection_service = UserCollectionService(db)
        user_collection_service.verify_user_access(user_id, file.collection_id)

        # Now safe to delete
        service.delete_file(file_id)
        return True
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to delete file: {e!s}") from e
