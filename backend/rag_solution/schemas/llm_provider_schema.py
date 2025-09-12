from datetime import datetime

from pydantic import UUID4, BaseModel, Field, SecretStr, field_validator, ConfigDict


class LLMProviderInput(BaseModel):
    """Schema for creating an LLM Provider."""

    name: str = Field(..., description="Name of the provider")
    base_url: str = Field(..., description="Base URL of the provider's API")
    api_key: SecretStr | None = Field(None, description="API key for authentication")
    org_id: str | None = Field(None, description="Organization ID, if applicable")
    project_id: str | None = Field(None, description="Project ID, if applicable")
    is_active: bool = Field(True, description="Indicates if the provider is active")
    is_default: bool = Field(False, description="Indicates if this is the default provider")
    user_id: UUID4 | None = Field(None, description="User ID who owns this provider")


class LLMProviderOutput(BaseModel):
    """Schema for returning an LLM Provider."""

    id: UUID4 = Field(..., description="Unique identifier of the provider")
    name: str = Field(..., description="Name of the provider")
    base_url: str = Field(..., description="Base URL of the provider's API")
    org_id: str | None = Field(None, description="Organization ID")
    project_id: str | None = Field(None, description="Project ID")
    is_active: bool = Field(..., description="Indicates if the provider is active")
    is_default: bool = Field(..., description="Indicates if this is the default provider")
    created_at: datetime = Field(..., description="Timestamp of creation")
    updated_at: datetime = Field(..., description="Timestamp of last update")

    model_config = ConfigDict(from_attributes=True)


class LLMProviderConfig(BaseModel):
    """Internal configuration model that includes credentials."""

    id: UUID4
    name: str
    base_url: str
    api_key: SecretStr
    org_id: str | None = None
    project_id: str | None = None
    is_active: bool
    is_default: bool
    created_at: datetime
    updated_at: datetime

    @field_validator("api_key", mode="before")
    @classmethod
    def convert_api_key_to_secret_str(cls, v):
        """Convert string API key to SecretStr."""
        if isinstance(v, str):
            print(f"DEBUG: Converting API key '{v}' to SecretStr")
            return SecretStr(v)
        print(f"DEBUG: API key is not a string: {type(v)} = {v}")
        return v

    model_config = ConfigDict(from_attributes=True)
