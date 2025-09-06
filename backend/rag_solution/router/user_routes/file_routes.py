"""File management routes."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import UUID4
from sqlalchemy.orm import Session

from core.config import Settings, get_settings
from rag_solution.core.dependencies import verify_user_access
from rag_solution.file_management.database import get_db
from rag_solution.schemas.file_schema import FileOutput
from rag_solution.schemas.user_schema import UserOutput
from rag_solution.services.file_management_service import FileManagementService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/files",
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
    db: Session = Depends(get_db),
    collection_id: UUID4 | None = None,
    user: UserOutput = Depends(verify_user_access),
    settings: Annotated[Settings, Depends(get_settings)] = Depends(get_settings)
) -> FileOutput:
    """Upload a file to a user's collection."""
    service = FileManagementService(db, settings)
    try:
        # Upload file and create file record
        return service.upload_and_create_file_record(file, user_id, collection_id or user_id, str(user_id))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to upload file: {e!s}") from e


@router.delete(
    "/files/{file_id}",
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
    db: Session = Depends(get_db),
    user: UserOutput = Depends(verify_user_access),
    settings: Annotated[Settings, Depends(get_settings)] = Depends(get_settings)
) -> bool:
    """Delete a file from a user's collection."""
    service = FileManagementService(db, settings)
    try:
        service.delete_file(file_id)
        return True
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to delete file: {e!s}") from e
