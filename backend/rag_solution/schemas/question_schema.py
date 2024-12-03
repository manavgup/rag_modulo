"""Schema definitions for question-related data structures."""

from uuid import UUID
from pydantic import BaseModel, ConfigDict

class QuestionInDB(BaseModel):
    """Database representation of a question."""
    id: UUID
    collection_id: UUID
    question: str

    model_config = ConfigDict(from_attributes=True)

class QuestionInput(BaseModel):
    """Input model for creating a question."""
    collection_id: UUID
    question: str

class QuestionOutput(BaseModel):
    """Output model for question data."""
    id: UUID
    collection_id: UUID
    question: str

    model_config = ConfigDict(from_attributes=True)
