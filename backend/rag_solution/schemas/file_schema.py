from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from vectordbs.data_types import FileMetadata


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
    metadata: FileMetadata | None = None
    document_id: str | None = None


class FileOutput(BaseModel):
    id: UUID
    collection_id: UUID
    filename: str | None = None
    file_path: str | None = None
    file_type: str | None = None
    metadata: FileMetadata | None = None
    document_id: str | None = None


class DocumentDelete(BaseModel):
    filenames: list[str]
