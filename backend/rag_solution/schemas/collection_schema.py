from datetime import datetime
from typing import List
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class FileInfo(BaseModel):
    id: UUID
    filename: str

class CollectionInput(BaseModel):
    name: str
    is_private: bool
    users: List[UUID] = []

class CollectionOutput(BaseModel):
    id: UUID
    name: str
    vector_db_name: str
    is_private: bool
    created_at: datetime
    updated_at: datetime
    user_ids: List[UUID]
    files: List[FileInfo]

    model_config = ConfigDict(from_attributes=True)

class CollectionInDB(BaseModel):
    id: UUID
    name: str
    is_private: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)