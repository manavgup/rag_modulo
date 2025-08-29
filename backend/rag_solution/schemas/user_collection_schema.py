from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from .collection_schema import CollectionStatus


class FileInfo(BaseModel):
    id: UUID
    filename: str

    model_config = ConfigDict(from_attributes=True)


class UserCollectionInput(BaseModel):
    user_id: UUID
    collection_id: UUID

    model_config = ConfigDict(from_attributes=True)


class UserCollectionOutput(BaseModel):
    id: UUID  # This will be the collection_id
    name: str
    vector_db_name: str
    is_private: bool
    created_at: datetime
    updated_at: datetime
    user_ids: list[UUID]
    files: list[FileInfo]
    status: CollectionStatus
    user_id: UUID  # Additional field specific to user-collection relationship
    collection_id: UUID  # Keep this for reference

    model_config = ConfigDict(from_attributes=True)


class UserCollectionInDB(BaseModel):
    user_id: UUID
    collection_id: UUID
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserCollectionDetailOutput(BaseModel):
    collection_id: UUID
    name: str
    is_private: bool
    created_at: datetime
    updated_at: datetime
    files: list[FileInfo]
    status: CollectionStatus

    model_config = ConfigDict(from_attributes=True)


class UserCollectionsOutput(BaseModel):
    user_id: UUID
    collections: list[UserCollectionDetailOutput]

    model_config = ConfigDict(from_attributes=True)
