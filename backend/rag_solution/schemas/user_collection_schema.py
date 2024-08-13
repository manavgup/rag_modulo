from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UserCollectionInput(BaseModel):
    user_id: UUID
    collection_id: UUID

class UserCollectionOutput(BaseModel):
    user_id: UUID
    collection_id: UUID

    model_config = ConfigDict(from_attributes=True)

class UserCollectionInDB(BaseModel):
    user_id: UUID
    collection_id: UUID
    joined_at: datetime
