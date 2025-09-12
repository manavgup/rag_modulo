from datetime import datetime

from pydantic import UUID4, BaseModel, ConfigDict, Field, field_validator


# 🆔 Base Parameters
class LLMParametersBase(BaseModel):
    name: str = Field(..., description="Name of the LLM parameter configuration")
    description: str | None = Field(None, description="Description of the LLM parameters")


# ⚙️ Core LLM Parameters
class LLMParametersInput(LLMParametersBase):
    user_id: UUID4 = Field(..., description="ID of the user who owns these parameters")
    max_new_tokens: int = Field(default=100, ge=1, le=2048, description="Maximum number of new tokens")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    top_k: int = Field(default=50, ge=1, le=100, description="Top-k sampling parameter")
    top_p: float = Field(default=1.0, ge=0.0, le=1.0, description="Top-p sampling parameter")
    repetition_penalty: float | None = Field(default=1.1, ge=1.0, le=2.0, description="Penalty for repeated tokens")
    is_default: bool = Field(default=False, description="Flag indicating if this is the default configuration")

    model_config = ConfigDict(strict=True, extra="forbid", title="LLM Parameters Input", frozen=False)

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        if v < 0.0 or v > 1.0:
            raise ValueError("Temperature must be between 0.0 and 1.0")
        return v


# 🟢 Output Schema
class LLMParametersOutput(LLMParametersBase):
    id: UUID4 = Field(..., description="Unique identifier for the LLM parameters")
    user_id: UUID4 = Field(..., description="ID of the user who owns these parameters")
    max_new_tokens: int = Field(..., description="Maximum number of new tokens")
    temperature: float = Field(..., description="Sampling temperature")
    top_k: int = Field(..., description="Top-k sampling parameter")
    top_p: float = Field(..., description="Top-p sampling parameter")
    repetition_penalty: float | None = Field(..., description="Penalty for repeated tokens")
    is_default: bool = Field(default=False, description="Flag indicating if this is the default configuration")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)

    def to_input(self) -> "LLMParametersInput":
        """Convert the current instance to an LLMParametersInput schema."""
        return LLMParametersInput(
            user_id=self.user_id,
            name=self.name,
            description=self.description,
            max_new_tokens=self.max_new_tokens,
            temperature=self.temperature,
            top_k=self.top_k,
            top_p=self.top_p,
            repetition_penalty=self.repetition_penalty,
            is_default=self.is_default,
        )


# 📊 In-Database Representation
class LLMParametersInDB(LLMParametersOutput):
    """Schema for representing LLM parameters in the database."""

    model_config = ConfigDict(strict=True, extra="ignore", title="LLM Parameters In DB", frozen=True)
