from datetime import datetime

from pydantic import BaseModel, ConfigDict, UUID4


class UserTeamInput(BaseModel):
    user_id: UUID4
    team_id: UUID4


class UserTeamOutput(BaseModel):
    user_id: UUID4
    team_id: UUID4
    role: str = "member"  # Default role
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserTeamInDB(BaseModel):
    user_id: UUID4
    team_id: UUID4
    joined_at: datetime
