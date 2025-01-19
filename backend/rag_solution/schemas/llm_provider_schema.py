"""Pydantic schemas for LLM Provider management with strong validation."""

from typing import Optional, Annotated, Dict, Any, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, UUID4, SecretStr, field_validator, model_validator


class ModelType(str, Enum):
    """Type of LLM model."""
    
    GENERATION = "generation"
    EMBEDDING = "embedding"


class LLMProviderInput(BaseModel):
    """Schema for creating a new LLM provider.
    
    Attributes:
        name: Unique identifier for the provider
        base_url: Base URL for the provider's API
        api_key: Authentication key for the provider
        org_id: Optional organization ID for the provider
        project_id: Optional project ID for the provider
    """
    
    name: Annotated[str, Field(
        min_length=1,
        max_length=255,
        pattern=r'^[a-zA-Z0-9_-]+$',
        examples=["watsonx", "openai"],
        description="Unique identifier for the provider"
    )]
    base_url: Annotated[str, Field(
        min_length=1,
        pattern=r'^https?://',
        examples=["https://api.openai.com"],
        description="Base URL for the provider's API"
    )]
    api_key: Annotated[SecretStr, Field(
        min_length=1,
        examples=["sk-..."],
        description="Authentication key for the provider"
    )]
    org_id: Optional[Annotated[str, Field(
        max_length=255,
        examples=["org-123"],
        description="Optional organization ID"
    )]] = None
    project_id: Optional[Annotated[str, Field(
        max_length=255,
        examples=["project-xyz"],
        description="Optional project ID"
    )]] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "watsonx",
                "base_url": "https://us-south.ml.cloud.ibm.com",
                "api_key": "sk-...",
                "project_id": "project-123"
            }
        }
    )


class LLMProviderOutput(BaseModel):
    """Schema for provider output with all fields.
    
    Attributes:
        id: Unique UUID for the provider
        name: Provider name
        base_url: Provider API base URL
        api_key: Authentication key for the provider
        org_id: Optional organization ID
        project_id: Optional project ID
        is_active: Whether the provider is active
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    
    id: UUID4
    name: str
    base_url: str  # Changed from HttpUrl to str for database compatibility
    api_key: str  # Added api_key field for UI display
    org_id: Optional[str] = None
    project_id: Optional[str] = None
    is_active: bool = True  # Default to True
    created_at: datetime
    updated_at: datetime

    @field_validator('created_at', 'updated_at', mode='before')
    @classmethod
    def validate_datetime(cls, v):
        """Handle SQLAlchemy datetime attributes."""
        if hasattr(v, '_sa_instance_state'):
            return v.isoformat()
        return v

    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "watsonx",
                "base_url": "https://us-south.ml.cloud.ibm.com",
                "api_key": "sk-...",
                "project_id": "project-123",
                "is_active": True,
                "created_at": "2024-01-08T12:00:00Z",
                "updated_at": "2024-01-08T12:00:00Z"
            }
        }
    )


class LLMProviderInDB(LLMProviderOutput):
    """Schema for provider in database, including sensitive fields.
    
    Currently identical to LLMProviderOutput since we've added api_key to the output schema.
    """
    pass


class LLMProviderModelInput(BaseModel):
    """Schema for creating a new provider model configuration.
    
    Attributes:
        provider_id: UUID of the associated provider
        model_id: Model identifier
        default_model_id: Default model identifier
        model_type: Type of model (generation/embedding)
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts
        batch_size: Batch processing size
        retry_delay: Delay between retries in seconds
        concurrency_limit: Maximum concurrent requests
        stream: Whether to use streaming responses
        rate_limit: Maximum requests per minute
        is_default: Whether this is the default model
        is_active: Whether the model is active
    """
    
    provider_id: UUID4
    model_id: Annotated[str, Field(
        min_length=1,
        max_length=255,
        examples=["gpt-4"],
        description="Model identifier"
    )]
    default_model_id: Annotated[str, Field(
        min_length=1,
        max_length=255,
        examples=["gpt-4-1106-preview"],
        description="Default model identifier"
    )]
    model_type: Annotated[ModelType, Field(
        description="Type of model (generation/embedding)"
    )]
    timeout: Annotated[int, Field(
        ge=1,
        le=300,
        default=30,
        examples=[30],
        description="Request timeout in seconds"
    )] = 30
    max_retries: Annotated[int, Field(
        ge=0,
        le=10,
        default=3,
        examples=[3],
        description="Maximum retry attempts"
    )] = 3
    batch_size: Annotated[int, Field(
        ge=1,
        le=100,
        default=10,
        examples=[10],
        description="Batch processing size"
    )] = 10
    retry_delay: Annotated[float, Field(
        ge=0.1,
        le=60.0,
        default=1.0,
        examples=[1.0],
        description="Delay between retries in seconds"
    )] = 1.0
    concurrency_limit: Annotated[int, Field(
        ge=1,
        le=100,
        default=10,
        examples=[10],
        description="Maximum concurrent requests"
    )] = 10
    stream: Annotated[bool, Field(
        default=False,
        examples=[False],
        description="Whether to use streaming responses"
    )] = False
    rate_limit: Annotated[int, Field(
        ge=1,
        le=1000,
        default=10,
        examples=[10],
        description="Maximum requests per minute"
    )] = 10
    is_default: Annotated[bool, Field(
        default=False,
        examples=[False],
        description="Whether this is the default model"
    )] = False
    is_active: Annotated[bool, Field(
        default=True,
        examples=[True],
        description="Whether the model is active"
    )] = True

    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        json_schema_extra={
            "example": {
                "provider_id": "123e4567-e89b-12d3-a456-426614174000",
                "model_id": "gpt-4",
                "default_model_id": "gpt-4-1106-preview",
                "model_type": "generation",
                "timeout": 30,
                "max_retries": 3,
                "batch_size": 10,
                "retry_delay": 1.0,
                "concurrency_limit": 10,
                "stream": False,
                "rate_limit": 10,
                "is_default": True,
                "is_active": True
            }
        }
    )


class LLMProviderModelOutput(BaseModel):
    """Schema for model configuration output with all fields.
    
    Attributes:
        id: Unique UUID for the model configuration
        provider_id: UUID of the associated provider
        model_id: Model identifier
        default_model_id: Default model identifier
        model_type: Type of model
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts
        batch_size: Batch processing size
        retry_delay: Delay between retries in seconds
        concurrency_limit: Maximum concurrent requests
        stream: Whether to use streaming responses
        rate_limit: Maximum requests per minute
        is_default: Whether this is the default model
        is_active: Whether the model is active
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    
    id: UUID4
    provider_id: UUID4
    model_id: str
    default_model_id: str
    model_type: ModelType
    timeout: Annotated[int, Field(ge=1, le=300)]
    max_retries: Annotated[int, Field(ge=0, le=10)]
    batch_size: Annotated[int, Field(ge=1, le=100)]
    retry_delay: Annotated[float, Field(ge=0.1, le=60.0)]
    concurrency_limit: Annotated[int, Field(ge=1, le=100)]
    stream: bool
    rate_limit: Annotated[int, Field(ge=1, le=1000)]
    is_default: bool = False
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    @field_validator('created_at', 'updated_at', mode='before')
    @classmethod
    def validate_datetime(cls, v):
        """Handle SQLAlchemy datetime attributes."""
        if hasattr(v, '_sa_instance_state'):
            return v.isoformat()
        return v

    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "provider_id": "123e4567-e89b-12d3-a456-426614174000",
                "model_id": "gpt-4",
                "default_model_id": "gpt-4-1106-preview",
                "model_type": "generation",
                "timeout": 30,
                "max_retries": 3,
                "batch_size": 10,
                "retry_delay": 1.0,
                "concurrency_limit": 10,
                "stream": False,
                "rate_limit": 10,
                "is_default": True,
                "is_active": True,
                "created_at": "2024-01-08T12:00:00Z",
                "updated_at": "2024-01-08T12:00:00Z"
            }
        }
    )


class LLMProviderModelInDB(LLMProviderModelOutput):
    """Schema for model configuration in database.
    
    Currently identical to LLMProviderModelOutput, but may include
    additional sensitive fields in the future.
    """
    pass
