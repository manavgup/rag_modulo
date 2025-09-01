from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, UUID4


class UserInDB(BaseModel):
    id: UUID4
    ibm_id: str
    email: EmailStr
    name: str
    role: str = Field(default="user")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserInput(BaseModel):
    id: UUID4 | None = None
    ibm_id: str = Field(..., min_length=1)
    email: EmailStr
    name: str = Field(..., min_length=1)
    role: str = Field(default="user")
    preferred_provider_id: UUID4 | None = Field(None, description="User's preferred LLM provider")  # 👈 Add this


class UserOutput(BaseModel):
    id: UUID4
    ibm_id: str
    email: EmailStr
    name: str
    role: str
    preferred_provider_id: UUID4 | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
