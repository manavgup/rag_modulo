from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from .user_schema import UserOutput
from typing import List, Optional

class TeamInDB(BaseModel):
    id: UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime
    member_count: int

    model_config = {
        "from_attributes": True
    }

class TeamInput(BaseModel):
    name: str
    description: str | None = None

class TeamOutput(BaseModel):
    name: str
    description: str | None = None
    users: Optional[List[UserOutput]] = None

class UserTeamInDB(BaseModel):
    user_id: UUID
    team_id: UUID
    joined_at: datetime

    model_config = {
        "from_attributes": True
    }

class UserTeamOutput(BaseModel):
    user_id: UUID
    team_id: UUID
    joined_at: datetime
