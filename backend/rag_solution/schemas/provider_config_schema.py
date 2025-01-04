"""Pydantic schemas for provider configuration."""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator

class ProviderRuntimeSettings(BaseModel):
    """Base runtime settings for providers."""
    
    timeout: int = Field(
        default=30,
        ge=1,
        description="Request timeout in seconds"
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        description="Maximum number of retry attempts"
    )
    batch_size: int = Field(
        default=10,
        ge=1,
        description="Size of batches for bulk operations"
    )
    retry_delay: float = Field(
        default=1.0,
        ge=0.0,
        description="Delay between retries in seconds"
    )

    @field_validator('timeout', 'max_retries', 'batch_size')
    @classmethod
    def validate_positive(cls, v: int, field: str) -> int:
        """Validate integer fields are positive."""
        if v <= 0:
            raise ValueError(f"{field} must be positive")
        return v

class ProviderExtendedSettings(ProviderRuntimeSettings):
    """Extended runtime settings for LLM providers."""
    
    concurrency_limit: int = Field(
        default=10,
        ge=1,
        description="Maximum concurrent requests"
    )
    stream: bool = Field(
        default=False,
        description="Whether to use streaming mode"
    )
    rate_limit: int = Field(
        default=10,
        ge=1,
        description="Maximum requests per second"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{
                "concurrency_limit": 5,
                "timeout": 60,
                "batch_size": 20,
                "stream": True,
                "rate_limit": 20,
                "max_retries": 3,
                "retry_delay": 1.0
            }]
        }
    )

class ProviderConfig(BaseModel):
    """Base configuration for LLM providers."""
    
    # Model identification
    model_id: str = Field(
        ...,
        description="Unique identifier for the model",
        min_length=1,
        max_length=255
    )
    provider_name: str = Field(
        ...,
        description="Name of the LLM provider",
        min_length=1,
        max_length=255
    )
    
    # Provider credentials
    api_key: str = Field(..., description="API key for provider authentication")
    api_url: Optional[str] = Field(None, description="API endpoint URL")
    project_id: Optional[str] = Field(None, description="Project ID")
    org_id: Optional[str] = Field(None, description="Organization ID")
    
    # Model settings
    default_model_id: str = Field(..., description="Default model ID for text generation")
    embedding_model: Optional[str] = Field(None, description="Model ID for embeddings")
    
    # Runtime settings
    runtime: ProviderRuntimeSettings = Field(
        default_factory=ProviderRuntimeSettings,
        description="Runtime configuration settings"
    )
    
    # Status
    is_active: bool = Field(
        True,
        description="Whether this model configuration is active"
    )

    model_config = ConfigDict(
        extra='allow',  # Allow extra fields for extensibility
        from_attributes=True
    )

    @field_validator('provider_name')
    @classmethod
    def validate_provider_name(cls, v: str) -> str:
        """Ensure provider name is lowercase and contains only valid characters."""
        v = v.lower()
        if not v.isalnum() and not v.replace('_', '').isalnum():
            raise ValueError("Provider name must contain only letters, numbers, and underscores")
        return v

class ProviderOutput(ProviderConfig):
    """Provider configuration with output fields."""
    
    id: int = Field(..., description="Unique identifier for the configuration")
    parameters_id: int = Field(..., description="ID of the associated LLM parameters")

class ProviderInDB(ProviderOutput):
    """Provider configuration with database fields."""
    
    last_verified: Optional[datetime] = Field(None, description="Timestamp of last verification")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

class ProviderUpdate(BaseModel):
    """Schema for updating provider configuration."""
    
    model_id: Optional[str] = None
    provider_name: Optional[str] = None
    api_key: Optional[str] = None
    api_url: Optional[str] = None
    project_id: Optional[str] = None
    org_id: Optional[str] = None
    default_model_id: Optional[str] = None
    embedding_model: Optional[str] = None
    parameters_id: Optional[int] = None
    runtime: Optional[ProviderRuntimeSettings] = None
    is_active: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)

class ProviderRegistry(BaseModel):
    """Response schema for provider registry queries."""
    
    total_providers: int = Field(..., description="Total number of registered providers")
    active_providers: int = Field(..., description="Number of active providers")
    providers: List[ProviderInDB] = Field(
        ...,
        description="List of registered provider configurations"
    )

    model_config = ConfigDict(from_attributes=True)
