from datetime import datetime

from pydantic import UUID4, BaseModel, ConfigDict

from .collection_schema import CollectionStatus


class FileInfo(BaseModel):
    id: UUID4
    filename: str

    model_config = ConfigDict(from_attributes=True)


class UserCollectionInput(BaseModel):
    user_id: UUID4
    collection_id: UUID4

    model_config = ConfigDict(from_attributes=True)


class UserCollectionOutput(BaseModel):
    id: UUID4 | None = None  # This will be the collection_id
    name: str | None = None
    vector_db_name: str | None = None
    is_private: bool | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    user_ids: list[UUID4] = []
    files: list[FileInfo] = []
    status: CollectionStatus | None = None
    user_id: UUID4 | None = None  # Additional field specific to user-collection relationship
    collection_id: UUID4 | None = None  # Keep this for reference

    model_config = ConfigDict(from_attributes=True)


class UserCollectionInDB(BaseModel):
    user_id: UUID4
    collection_id: UUID4
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserCollectionDetailOutput(BaseModel):
    collection_id: UUID4
    name: str
    is_private: bool
    created_at: datetime
    updated_at: datetime
    files: list[FileInfo]
    status: CollectionStatus

    model_config = ConfigDict(from_attributes=True)


class UserCollectionsOutput(BaseModel):
    user_id: UUID4
    collections: list[UserCollectionDetailOutput]

    model_config = ConfigDict(from_attributes=True)
