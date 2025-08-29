from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, SecretStr


class LLMProviderInput(BaseModel):
    """Schema for creating an LLM Provider."""

    name: str = Field(..., description="Name of the provider")
    base_url: str = Field(..., description="Base URL of the provider's API")
    api_key: SecretStr | None = Field(None, description="API key for authentication")
    org_id: str | None = Field(None, description="Organization ID, if applicable")
    project_id: str | None = Field(None, description="Project ID, if applicable")
    is_active: bool = Field(True, description="Indicates if the provider is active")
    is_default: bool = Field(False, description="Indicates if this is the default provider")


class LLMProviderOutput(BaseModel):
    """Schema for returning an LLM Provider."""

    id: UUID = Field(..., description="Unique identifier of the provider")
    name: str = Field(..., description="Name of the provider")
    base_url: str = Field(..., description="Base URL of the provider's API")
    org_id: str | None = Field(None, description="Organization ID")
    project_id: str | None = Field(None, description="Project ID")
    is_active: bool = Field(..., description="Indicates if the provider is active")
    is_default: bool = Field(..., description="Indicates if this is the default provider")
    created_at: datetime = Field(..., description="Timestamp of creation")
    updated_at: datetime = Field(..., description="Timestamp of last update")

    class Config:
        from_attributes = True


class LLMProviderConfig(BaseModel):
    """Internal configuration model that includes credentials."""

    id: UUID
    name: str
    base_url: str
    api_key: SecretStr
    org_id: str | None = None
    project_id: str | None = None
    is_active: bool
    is_default: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
