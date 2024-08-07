from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime

class UserTeamInput(BaseModel):
    user_id: UUID
    team_id: UUID

class UserTeamOutput(BaseModel):
    user_id: UUID
    team_id: UUID
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)

class UserTeamInDB(BaseModel):
    user_id: UUID
    team_id: UUID
    joined_at: datetime
