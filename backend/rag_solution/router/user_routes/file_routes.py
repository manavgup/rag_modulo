"""File management routes."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from core.authorization import authorize_decorator
from rag_solution.file_management.database import get_db
from rag_solution.schemas.file_schema import FileOutput
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
@authorize_decorator(role="user")
async def upload_file(
    user_id: UUID,
    file: UploadFile,
    request: Request,
    db: Session = Depends(get_db),
    collection_id: UUID | None = None,
) -> FileOutput:
    """Upload a file to a user's collection."""
    if not hasattr(request.state, "user") or request.state.user["uuid"] != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized to upload file")

    service = FileManagementService(db)
    try:
        # Upload file and create file record
        return service.upload_and_create_file_record(
            file, user_id, collection_id or user_id, str(user_id)
        )
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
@authorize_decorator(role="user")
async def delete_file(user_id: UUID, file_id: UUID, request: Request, db: Session = Depends(get_db)) -> bool:
    """Delete a file from a user's collection."""
    if not hasattr(request.state, "user") or request.state.user["uuid"] != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized to delete file")

    service = FileManagementService(db)
    try:
        return service.delete_file(file_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to delete file: {e!s}") from e
