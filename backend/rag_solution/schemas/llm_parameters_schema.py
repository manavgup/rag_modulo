from typing import Optional
from datetime import datetime
from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
    ConfigDict,
    computed_field,
    ValidationInfo
)
from typing_extensions import Annotated

class LLMParametersBase(BaseModel):
    """Base schema for LLM generation parameters."""
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{
                "max_new_tokens": 100,
                "temperature": 0.7,
                "top_k": 50,
                "top_p": 1.0,
                "repetition_penalty": 1.1
            }]
        },
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid"
    )
    
    max_new_tokens: int = Field(
        default=100,
        ge=1,
        le=2048,
        description="Maximum number of tokens to generate"
    )
    min_new_tokens: Optional[int] = Field(
        default=None,
        ge=1,
        le=2048,
        description="Minimum number of tokens to generate"
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature; higher means more random"
    )
    top_k: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Number of highest probability tokens to consider"
    )
    top_p: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Cumulative probability threshold for token sampling"
    )
    random_seed: Optional[int] = Field(
        default=None,
        description="Seed for random number generation"
    )
    repetition_penalty: Optional[float] = Field(
        default=1.1,
        ge=1.0,
        le=2.0,
        description="Penalty for repeating tokens; higher values discourage repetition"
    )
    
    @model_validator(mode='after')
    def validate_min_tokens(self) -> 'LLMParametersBase':
        """Validate min_new_tokens is less than max_new_tokens."""
        if (self.min_new_tokens is not None and 
            self.min_new_tokens > self.max_new_tokens):
            raise ValueError('min_new_tokens must be less than or equal to max_new_tokens')
        return self

    @computed_field(return_type=bool)
    @property
    def is_deterministic(self) -> bool:
        """Check if parameter set will produce deterministic output."""
        return (
            self.temperature == 0.0 and
            self.top_p == 1.0 and
            self.random_seed is not None
        )

class LLMParametersCreate(LLMParametersBase):
    """Schema for creating LLM parameters."""
    name: Annotated[str, Field(
        description="Name of the parameter set",
        min_length=1,
        max_length=255,
        examples=["gpt4-creative", "llama-precise"]
    )]
    description: Annotated[Optional[str], Field(
        default=None,
        description="Description of the parameter set",
        examples=["Creative writing parameters with high temperature"]
    )]
    is_default: Annotated[bool, Field(
        default=False,
        description="Whether this is the default parameter set"
    )]

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{
                "name": "gpt4-creative",
                "description": "Creative writing parameters",
                "max_new_tokens": 100,
                "temperature": 0.8,
                "top_k": 50,
                "top_p": 0.9,
                "repetition_penalty": 1.1,
                "is_default": False
            }]
        },
        from_attributes=True,
        validate_assignment=True,
        str_strip_whitespace=True,
        extra="forbid"
    )

class LLMParametersUpdate(BaseModel):
    """Schema for updating LLM parameters."""
    name: Annotated[Optional[str], Field(
        min_length=1,
        max_length=255,
        examples=["gpt4-creative-v2"]
    )] = None
    description: Optional[str] = None
    max_new_tokens: Annotated[Optional[int], Field(
        ge=1,
        le=2048,
        examples=[150]
    )] = None
    min_new_tokens: Annotated[Optional[int], Field(
        ge=1,
        le=2048,
        examples=[50]
    )] = None
    temperature: Annotated[Optional[float], Field(
        ge=0.0,
        le=2.0,
        examples=[0.8]
    )] = None
    top_k: Annotated[Optional[int], Field(
        ge=1,
        le=100,
        examples=[40]
    )] = None
    top_p: Annotated[Optional[float], Field(
        ge=0.0,
        le=1.0,
        examples=[0.9]
    )] = None
    random_seed: Annotated[Optional[int], Field(
        examples=[42]
    )] = None
    repetition_penalty: Annotated[Optional[float], Field(
        ge=1.0,
        le=2.0,
        examples=[1.1]
    )] = None
    is_default: Optional[bool] = None

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [{
                "name": "gpt4-creative-v2",
                "temperature": 0.8,
                "top_k": 40,
                "repetition_penalty": 1.1,
                "description": "Updated creative parameters"
            }]
        }
    )

    @model_validator(mode='after')
    def validate_update(self) -> 'LLMParametersUpdate':
        """Validate update parameters."""
        if all(v is None for v in self.model_dump().values()):
            raise ValueError("At least one field must be provided for update")
        return self

class LLMParametersResponse(LLMParametersBase):
    """Schema for LLM parameters response."""
    id: Annotated[int, Field(description="Unique identifier")]
    name: Annotated[str, Field(
        min_length=1,
        max_length=255,
        description="Parameter set name"
    )]
    description: Optional[str] = Field(
        default=None,
        description="Parameter set description"
    )
    is_default: bool = Field(
        default=False,
        description="Whether this is the default parameter set"
    )
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [{
                "id": 1,
                "name": "gpt4-creative",
                "description": "Creative writing parameters",
                "max_new_tokens": 100,
                "temperature": 0.8,
                "top_k": 50,
                "top_p": 0.9,
                "repetition_penalty": 1.1,
                "is_default": False,
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00"
            }]
        }
    )
