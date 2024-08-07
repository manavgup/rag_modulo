from __future__ import annotations
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from uuid import UUID
from datetime import datetime
from typing import List

class UserInDB(BaseModel):
    id: UUID
    ibm_id: str
    email: EmailStr
    name: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class UserInput(BaseModel):
    ibm_id: str = Field(..., min_length=1)
    email: EmailStr
    name: str = Field(..., min_length=1)

class UserOutput(BaseModel):
    id: UUID
    ibm_id: str
    email: EmailStr
    name: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
