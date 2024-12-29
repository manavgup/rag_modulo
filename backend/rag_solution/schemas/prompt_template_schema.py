from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator
from uuid import UUID, uuid4

from rag_solution.models.prompt_template import PromptTemplate

class PromptTemplateBase(BaseModel):
    """Base schema for prompt templates with common fields."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Template name")
    provider: str = Field(..., min_length=1, max_length=50, description="LLM provider")
    description: Optional[str] = Field(None, description="Template description")
    system_prompt: str = Field(..., min_length=1, description="System prompt for the LLM")
    context_prefix: str = Field(..., min_length=1, max_length=255, description="Prefix for context section")
    query_prefix: str = Field(..., min_length=1, max_length=255, description="Prefix for query section")
    answer_prefix: str = Field(..., min_length=1, max_length=255, description="Prefix for answer section")
    is_default: bool = Field(False, description="Whether this is the default template for the provider")

    model_config = ConfigDict(
        json_schema_extra={
            "example": PromptTemplate.EXAMPLE_TEMPLATES["watsonx"]
        }
    )

class PromptTemplateCreate(PromptTemplateBase):
    """Schema for creating a new prompt template."""
    
    @field_validator("provider")
    def validate_provider(cls, v: str) -> str:
        """Validate provider name."""
        valid_providers = {"watsonx", "openai", "anthropic", "llama2", "tii"}
        if v.lower() not in valid_providers:
            raise ValueError(f"Invalid provider. Must be one of: {', '.join(valid_providers)}")
        return v.lower()

class PromptTemplateUpdate(BaseModel):
    """Schema for updating an existing prompt template."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    system_prompt: Optional[str] = Field(None, min_length=1)
    context_prefix: Optional[str] = Field(None, min_length=1, max_length=255)
    query_prefix: Optional[str] = Field(None, min_length=1, max_length=255)
    answer_prefix: Optional[str] = Field(None, min_length=1, max_length=255)
    is_default: Optional[bool] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "custom_watsonx",
                "description": "Updated description",
                "system_prompt": "Updated system prompt",
                "is_default": True
            }
        }
    )

class PromptTemplateResponse(PromptTemplateBase):
    """Schema for prompt template responses including metadata."""
    
    id: UUID = Field(..., description="Template unique identifier")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                **PromptTemplate.EXAMPLE_TEMPLATES["watsonx"],
                "id": str(uuid4()),
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-02T00:00:00Z"
            }
        }
    )
