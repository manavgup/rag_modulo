"""Pydantic schemas for provider configuration."""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class ProviderModelConfigBase(BaseModel):
    """Base schema for provider model configuration."""
    
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
    is_active: bool = Field(
        True,
        description="Whether this model configuration is active"
    )
    parameters_id: int = Field(
        ...,
        description="ID of the associated LLM parameters"
    )

class ProviderModelConfigCreate(ProviderModelConfigBase):
    """Schema for creating a new provider model configuration."""
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
    is_active: Optional[bool] = Field(
        None,
        description="Whether this model configuration is active"
    )
    parameters_id: Optional[int] = Field(
        None,
        description="ID of the associated LLM parameters"
    )

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
    providers: list[ProviderModelConfigResponse] = Field(
        ...,
        description="List of registered provider configurations"
    )

    model_config = ConfigDict(from_attributes=True)
