from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from typing import List
from uuid import UUID

from backend.rag_solution.services.file_management_service import FileManagementService, get_file_management_service
from backend.rag_solution.schemas.file_schema import FileOutput

router = APIRouter(prefix="/files", tags=["files"])

@router.post("/{user_id}/{collection_id}", response_model=FileOutput)
async def upload_file(
    user_id: UUID,
    collection_id: UUID,
    file: UploadFile = File(...),
    file_service: FileManagementService = Depends(get_file_management_service)
):
    try:
        file_path = await file_service.save_file(file, user_id, collection_id)
        return FileOutput(
            filename=file.filename,
            filepath=str(file_path),
            file_type=file.content_type
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{user_id}/{collection_id}", response_model=List[str])
async def get_collection_files(
    user_id: UUID,
    collection_id: UUID,
    file_service: FileManagementService = Depends(get_file_management_service)
):
    return file_service.get_files(user_id, collection_id)

@router.get("/{user_id}/{collection_id}/{filename}")
async def get_file_path(
    user_id: UUID,
    collection_id: UUID,
    filename: str,
    file_service: FileManagementService = Depends(get_file_management_service)
):
    file_path = file_service.get_file_path(user_id, collection_id, filename)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return {"file_path": str(file_path)}
