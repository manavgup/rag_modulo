from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional
from .file_schema import FileOutput

class CollectionInDB(BaseModel):
    id: UUID
    name: str
    is_private: bool
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }

class CollectionInput(BaseModel):
    name: str
    is_private: bool
    user_id: UUID

class CollectionOutput(BaseModel):
    name: Optional[str] = None
    is_private: Optional[bool] = None
    files: Optional[list[FileOutput]] = None
