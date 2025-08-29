"""Schema definitions for question-related data structures."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class QuestionBase(BaseModel):
    """Base schema for question data."""

    collection_id: UUID = Field(..., description="ID of the collection this question belongs to")
    question: str = Field(..., min_length=10, max_length=500, description="The question text")

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)

    @field_validator("question")
    @classmethod
    def validate_question_format(cls, v: str) -> str:
        """Validate question format."""
        v = v.strip()
        if not v.endswith("?"):
            raise ValueError("Question must end with a question mark")
        return v


class QuestionInput(QuestionBase):
    """Input model for creating a question."""

    question_metadata: dict | None = Field(default=None, description="Optional metadata for the question")

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")


class QuestionInDB(QuestionBase):
    """Database representation of a question."""

    id: UUID = Field(..., description="Unique identifier for the question")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when the question was created")
    question_metadata: dict | None = Field(default=None, description="Optional metadata for the question")

    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        validate_assignment=True,
        json_encoders={datetime: lambda v: v.isoformat()},
    )


class QuestionOutput(QuestionBase):
    """Output model for question data."""

    id: UUID = Field(..., description="Unique identifier for the question")
    created_at: datetime = Field(..., description="Timestamp when the question was created")
    question_metadata: dict | None = Field(default=None, description="Optional metadata for the question")

    model_config = ConfigDict(from_attributes=True, json_encoders={datetime: lambda v: v.isoformat()})
