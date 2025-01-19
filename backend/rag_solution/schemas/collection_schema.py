from datetime import datetime
from typing import List
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from enum import Enum

class CollectionStatus(str, Enum):
    CREATED = "created"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"

class FileInfo(BaseModel):
    id: UUID
    filename: str

    model_config = ConfigDict(from_attributes=True)

class CollectionInput(BaseModel):
    name: str
    is_private: bool
    users: List[UUID] = []
    status: CollectionStatus = CollectionStatus.CREATED

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            UUID: lambda v: str(v),  # Convert UUID to string during serialization
        }
    )

class CollectionOutput(BaseModel):
    id: UUID
    name: str
    vector_db_name: str
    is_private: bool
    created_at: datetime
    updated_at: datetime
    user_ids: List[UUID]
    files: List[FileInfo]
    status: CollectionStatus

    model_config = ConfigDict(from_attributes=True)

class CollectionInDB(BaseModel):
    id: UUID
    name: str
    is_private: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)