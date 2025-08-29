from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


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
    users: list[UUID] = []
    status: CollectionStatus = CollectionStatus.CREATED

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            UUID: lambda v: str(v),  # Convert UUID to string during serialization
        },
    )


class CollectionOutput(BaseModel):
    id: UUID
    name: str
    vector_db_name: str
    is_private: bool
    created_at: datetime
    updated_at: datetime
    user_ids: list[UUID]
    files: list[FileInfo]
    status: CollectionStatus

    model_config = ConfigDict(from_attributes=True)


class CollectionInDB(BaseModel):
    id: UUID
    name: str
    is_private: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
