from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional

class FileInDB(BaseModel):
    id: UUID
    collection_id: UUID
    filename: str
    filepath: str
    file_type: str
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }

class FileInput(BaseModel):
    collection_id: UUID
    filename: str
    filepath: str
    file_type: str

class FileOutput(BaseModel):
    filename: Optional[str] = None
    filepath: Optional[str] = None
    file_type: Optional[str] = None
