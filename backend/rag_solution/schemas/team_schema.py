from datetime import datetime

from pydantic import BaseModel, ConfigDict, UUID4

from rag_solution.schemas.user_schema import UserOutput


class TeamInDB(BaseModel):
    id: UUID4
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TeamInput(BaseModel):
    name: str
    description: str | None = None


class TeamOutput(BaseModel):
    id: UUID4
    name: str
    description: str | None = None
    users: list[UserOutput] | None = None

    model_config = ConfigDict(from_attributes=True)
