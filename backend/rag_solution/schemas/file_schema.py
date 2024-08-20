from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

class FileMetadata(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    keywords: Optional[str] = None
    creator: Optional[str] = None
    producer: Optional[str] = None
    creationDate: Optional[str] = None
    modDate: Optional[str] = None
    total_pages: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

class FileInDB(BaseModel):
    id: UUID
    collection_id: UUID
    filename: str
    file_path: str
    file_type: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class FileInput(BaseModel):
    collection_id: UUID
    filename: str
    file_path: str
    file_type: str
    metadata: Optional[FileMetadata] = None

class FileOutput(BaseModel):
    id: UUID
    collection_id: UUID
    filename: Optional[str] = None
    file_path: Optional[str] = None
    file_type: Optional[str] = None
    metadata: Optional[FileMetadata] = None

class DocumentDelete(BaseModel):
    user_id: UUID
    collection_id: UUID
    filenames: List[str]
