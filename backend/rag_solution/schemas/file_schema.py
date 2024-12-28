from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from vectordbs.data_types import FileMetadata 

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
    document_id: Optional[str] = None

class FileOutput(BaseModel):
    id: UUID
    collection_id: UUID
    filename: Optional[str] = None
    file_path: Optional[str] = None
    file_type: Optional[str] = None
    metadata: Optional[FileMetadata] = None
    document_id: Optional[str] = None 

class DocumentDelete(BaseModel):    
    filenames: List[str]
