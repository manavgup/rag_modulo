"""Pydantic schemas for provider configuration."""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator

class ProviderModelConfigBase(BaseModel):
    """Base schema for provider model configuration.
    
    Core configuration for LLM providers including:
    - Model identification
    - Provider credentials
    - Model settings
    - Runtime settings
    """
    
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
    parameters_id: int = Field(..., description="ID of the associated LLM parameters")
    
    # Runtime settings
    timeout: int = Field(default=30, description="Request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum number of retry attempts")
    batch_size: int = Field(default=10, description="Batch size for bulk operations")
    
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

    @field_validator('timeout', 'max_retries', 'batch_size')
    @classmethod
    def validate_positive(cls, v: int, field: str) -> int:
        """Validate integer fields are positive."""
        if v <= 0:
            raise ValueError(f"{field} must be positive")
        return v

class ProviderModelConfigCreate(ProviderModelConfigBase):
    """Schema for creating a new provider model configuration.
    
    This inherits directly from the base as all fields are required
    for creation, with the same validation rules.
    """
    pass

class ProviderModelConfigUpdate(BaseModel):
    """Schema for updating an existing provider model configuration."""
    
    model_id: Optional[str] = Field(
        None,
        description="Unique identifier for the model",
        min_length=1,
        max_length=255
    )
    provider_name: Optional[str] = Field(
        None,
        description="Name of the LLM provider",
        min_length=1,
        max_length=255
    )
    api_key: Optional[str] = Field(None, description="API key for provider authentication")
    api_url: Optional[str] = Field(None, description="API endpoint URL")
    project_id: Optional[str] = Field(None, description="Project ID")
    org_id: Optional[str] = Field(None, description="Organization ID")
    default_model_id: Optional[str] = Field(None, description="Default model ID for text generation")
    embedding_model: Optional[str] = Field(None, description="Model ID for embeddings")
    parameters_id: Optional[int] = Field(None, description="ID of the associated LLM parameters")
    timeout: Optional[int] = Field(None, description="Request timeout in seconds")
    max_retries: Optional[int] = Field(None, description="Maximum number of retry attempts")
    batch_size: Optional[int] = Field(None, description="Batch size for bulk operations")
    is_active: Optional[bool] = Field(None, description="Whether this model configuration is active")

class ProviderModelConfigResponse(ProviderModelConfigBase):
    """Schema for provider model configuration responses."""
    
    id: int = Field(..., description="Unique identifier for the configuration")
    last_verified: Optional[datetime] = Field(
        None,
        description="Timestamp of last verification"
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)

class ProviderRegistryResponse(BaseModel):
    """Schema for provider registry responses."""
    
    total_providers: int = Field(..., description="Total number of registered providers")
    active_providers: int = Field(..., description="Number of active providers")
    providers: List[ProviderModelConfigResponse] = Field(
        ...,
        description="List of registered provider configurations"
    )

    model_config = ConfigDict(from_attributes=True)
