from datetime import datetime
from uuid import UUID
from typing import List
from pydantic import BaseModel, ConfigDict
from .collection_schema import CollectionStatus

class UserCollectionInput(BaseModel):
    user_id: UUID
    collection_id: UUID

    model_config = ConfigDict(from_attributes=True)

class UserCollectionOutput(BaseModel):
    user_id: UUID
    collection_id: UUID

    model_config = ConfigDict(from_attributes=True)

class UserCollectionInDB(BaseModel):
    user_id: UUID
    collection_id: UUID
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)

class FileInfo(BaseModel):
    id: UUID
    filename: str

class UserCollectionDetailOutput(BaseModel):
    collection_id: UUID
    name: str
    is_private: bool
    created_at: datetime
    updated_at: datetime
    files: List[FileInfo]
    status: CollectionStatus

    model_config = ConfigDict(from_attributes=True) 

class UserCollectionsOutput(BaseModel):
    user_id: UUID
    collections: List[UserCollectionDetailOutput]

    model_config = ConfigDict(from_attributes=True)