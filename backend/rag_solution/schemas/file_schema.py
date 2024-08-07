from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, List

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

class FileOutput(BaseModel):
    id: UUID
    filename: Optional[str] = None
    file_path: Optional[str] = None
    file_type: Optional[str] = None

class DocumentDelete(BaseModel):
    user_id: UUID
    collection_id: UUID
    filenames: List[str]
