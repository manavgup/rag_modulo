from datetime import datetime
from enum import Enum

from pydantic import UUID4, BaseModel, ConfigDict


class CollectionStatus(str, Enum):
    CREATED = "created"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


class FileInfo(BaseModel):
    id: UUID4
    filename: str
    file_size_bytes: int | None = None

    model_config = ConfigDict(from_attributes=True)


class CollectionInput(BaseModel):
    name: str
    is_private: bool
    users: list[UUID4] = []
    status: CollectionStatus = CollectionStatus.CREATED

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            UUID4: lambda v: str(v),  # Convert UUID to string during serialization
        },
    )


class CollectionOutput(BaseModel):
    id: UUID4
    name: str
    vector_db_name: str
    is_private: bool
    created_at: datetime
    updated_at: datetime
    user_ids: list[UUID4] = []
    files: list[FileInfo] = []
    status: CollectionStatus

    model_config = ConfigDict(from_attributes=True)


class CollectionInDB(BaseModel):
    id: UUID4
    name: str
    is_private: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
