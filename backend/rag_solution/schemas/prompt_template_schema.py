from pydantic import BaseModel, Field, UUID4, ConfigDict, field_validator, model_validator
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum
import json
import re

class PromptTemplateType(str, Enum):
    """Enum for prompt template types."""
    RAG_QUERY = "RAG_QUERY"
    QUESTION_GENERATION = "QUESTION_GENERATION" 
    RESPONSE_EVALUATION = "RESPONSE_EVALUATION"
    CUSTOM = "CUSTOM"

class PromptTemplateBase(BaseModel):
    """Base schema for prompt templates."""
    name: str = Field(..., min_length=1, max_length=255)
    user_id: UUID4
    template_type: PromptTemplateType = PromptTemplateType.CUSTOM
    system_prompt: Optional[str] = None
    template_format: str = Field(..., min_length=1)
    input_variables: Dict[str, str] = Field(default_factory=dict)
    example_inputs: Optional[Dict[str, Any]] = Field(default_factory=dict)
    context_strategy: Optional[Dict[str, Any]] = None
    max_context_length: Optional[int] = Field(None, gt=0)
    stop_sequences: Optional[List[str]] = None
    is_default: bool = False
    validation_schema: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(
        strict=True, 
        extra="forbid",
        validate_assignment=True,
        populate_by_name=True
    )

    @field_validator('user_id', mode='before')
    @classmethod
    def parse_user_id(cls, v):
        """Ensure user_id is a valid UUID, converting from string if needed."""
        if isinstance(v, str):
            return UUID4(v)
        return v

    @model_validator(mode='after')
    def validate_template_variables(self) -> 'PromptTemplateBase':
        """Validate that all template variables are defined in input_variables."""
        variables = set(re.findall(r"\{(\w+)\}", self.template_format))
        defined_vars = set(self.input_variables.keys())
        missing = variables - defined_vars

        if missing:
            raise ValueError(f"Template variables missing in input_variables: {missing}")
        
        return self
    
    @field_validator('template_format')
    @classmethod
    def validate_template_format(cls, v: str) -> str:
        """Validate template format syntax."""
        if not re.search(r"\{(\w+)\}", v):
            raise ValueError("Template format must contain at least one variable in {varname} format")
        return v

    @field_validator('input_variables')
    @classmethod
    def validate_variables(cls, v: Dict[str, str]) -> Dict[str, str]:
        """Validate input variables."""
        if not v:
            raise ValueError("At least one input variable must be defined")
        return v
    
    @field_validator('system_prompt')
    @classmethod
    def validate_system_prompt(cls, v: Optional[str]) -> Optional[str]:
        """Validate system prompt exists."""
        if not v:
            return "You are a helpful AI assistant."  # Default prompt
        return v

class PromptTemplateInput(PromptTemplateBase):
    """Input schema for creating/updating prompt templates."""
    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        validate_assignment=True,
        populate_by_name=True
    )

    @field_validator('template_type', mode='before')
    @classmethod
    def enforce_enum(cls, v):
        """Convert string to Enum if needed."""
        if isinstance(v, str):
            return PromptTemplateType(v)  # Convert string to Enum
        return v

class PromptTemplateOutput(PromptTemplateBase):
    """Output schema for prompt templates."""
    id: UUID4
    user_id: UUID4
    created_at: datetime
    updated_at: datetime
    template_type: PromptTemplateType

    model_config = ConfigDict(
        from_attributes=True
    )

    @field_validator('template_type', mode='before')
    @classmethod
    def validate_template_type(cls, v):
        """Ensure template_type is an instance of the Enum."""
        if isinstance(v, str):
            return PromptTemplateType(v)  # Convert string to Enum
        elif isinstance(v, PromptTemplateType):
            return v
        raise ValueError(f"Invalid template_type: {v}")

class PromptTemplateInDB(PromptTemplateOutput):
    """Database schema for prompt templates."""
    pass