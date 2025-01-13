from pydantic import BaseModel, Field, UUID4, ConfigDict, field_validator, model_validator
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum, auto


class PromptTemplateType(str, Enum):
    """Enum for prompt template types."""
    RAG_QUERY = "RAG_QUERY"
    QUESTION_GENERATION = "QUESTION_GENERATION" 
    RESPONSE_EVALUATION = "RESPONSE_EVALUATION"
    CUSTOM = "CUSTOM"


class PromptTemplateBase(BaseModel):
    """Base schema for prompt templates."""
    name: str = Field(..., min_length=1, max_length=255)
    provider: str = Field(..., min_length=1, max_length=50)
    template_type: PromptTemplateType = Field(default=PromptTemplateType.CUSTOM)
    system_prompt: Optional[str] = None
    template_format: str = Field(..., min_length=1)
    input_variables: Dict[str, str] = Field(default_factory=dict)
    example_inputs: Dict[str, Any] = Field(default_factory=dict)
    context_strategy: Optional[Dict[str, Any]] = None
    max_context_length: Optional[int] = Field(None, gt=0)
    stop_sequences: Optional[List[str]] = None
    is_default: bool = False
    validation_schema: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(strict=True, extra="forbid")

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """Validate provider name."""
        valid_providers = {"watsonx", "openai", "anthropic", "llama2"}
        if v.lower() not in valid_providers:
            raise ValueError(f"Invalid provider. Must be one of: {', '.join(valid_providers)}")
        return v.lower()

    @model_validator(mode="after")
    def validate_template(self) -> "PromptTemplateBase":
        """Validate template format matches input variables."""
        import re
        variables = re.findall(r"\{(\w+)\}", self.template_format)
        missing_vars = [var for var in variables if var not in self.input_variables]
        if missing_vars:
            raise ValueError(f"Template variables missing in input_variables: {missing_vars}")
        return self


class PromptTemplateInput(PromptTemplateBase):
    """Input schema for creating/updating prompt templates."""
    pass


class PromptTemplateOutput(PromptTemplateBase):
    """Output schema for prompt templates."""
    id: UUID4
    user_id: UUID4
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(strict=True, extra="ignore", frozen=True)
    
    @field_validator('template_type', mode='before')
    @classmethod
    def validate_template_type(cls, v):
        """Handle both string and enum instances."""
        if isinstance(v, str):
            return PromptTemplateType(v)
        return v


class PromptTemplateInDB(PromptTemplateOutput):
    """Database schema for prompt templates."""
    pass