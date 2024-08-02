from fastapi import APIRouter, Depends, HTTPException, UploadFile
from typing import List
from uuid import UUID
from sqlalchemy.orm import Session

from rag_solution.services.file_management_service import FileManagementService
from rag_solution.schemas.file_schema import FileOutput, DocumentDelete
from rag_solution.file_management.database import get_db

router = APIRouter(prefix="/api/files", tags=["files"])

@router.post("/{user_id}/{collection_id}", response_model=FileOutput)
def upload_file(user_id: UUID, collection_id: UUID, file: UploadFile, db: Session = Depends(get_db)):
    _file_service = FileManagementService(db)
    return _file_service.upload_and_create_file_record(file, user_id, collection_id)

@router.get("/{user_id}/{collection_id}", response_model=List[str])
def get_collection_files(user_id: UUID, collection_id: UUID, db: Session = Depends(get_db)):
    _file_service = FileManagementService(db)
    return _file_service.get_files(user_id, collection_id)

@router.get("/{user_id}/{collection_id}/{filename}")
def get_file_path(user_id: UUID, collection_id: UUID, filename: str, db: Session = Depends(get_db)):
    _file_service = FileManagementService(db)
    file_path = _file_service.get_file_path(user_id, collection_id, filename)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return {"file_path": str(file_path)}

@router.delete("/", response_model=bool)
def delete_files(doc_delete: DocumentDelete, db: Session = Depends(get_db)):
    _file_service = FileManagementService(db)
    return _file_service.delete_files(doc_delete.user_id, doc_delete.collection_id, doc_delete.filenames)
