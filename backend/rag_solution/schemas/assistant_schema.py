from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

class AssistantDB(BaseModel):
    id: UUID
    query: str
    context: Optional[str] = None
    max_tokens: Optional[int] = 100
    response: str
    confidence: Optional[float] = None
    error: Optional[str] = None
    user_id: Optional[UUID] = None          #Confirm if relate to user or team
    timestamp: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class AssistantInput(BaseModel):
    query: str
    context: Optional[str] = None
    max_tokens: Optional[int] = 100
    response: str
    confidence: Optional[float] = None
    error: Optional[str] = None
    user_id: Optional[UUID] = None 

class AssistantOutput(BaseModel):
    id: UUID
    query: str
    context: Optional[str] = None
    max_tokens: Optional[int] = 100
    response: str
    confidence: Optional[float] = None
    error: Optional[str] = None
    user_id: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)
