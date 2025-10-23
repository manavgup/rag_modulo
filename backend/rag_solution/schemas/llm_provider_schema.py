from datetime import datetime

from pydantic import UUID4, BaseModel, ConfigDict, Field, SecretStr, field_validator


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


class LLMProviderUpdate(BaseModel):
    """Schema for partial updates to LLM providers.

    All fields are optional to support partial updates from API.
    Use exclude_unset=True when converting to dict to only update provided fields.
    """

    name: str | None = None
    base_url: str | None = None
    api_key: SecretStr | None = None
    org_id: str | None = None
    project_id: str | None = None
    is_active: bool | None = None
    is_default: bool | None = None
    user_id: UUID4 | None = None


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
    def convert_api_key_to_secret_str(cls, v: str | SecretStr) -> SecretStr:
        """Convert string API key to SecretStr.

        Args:
            v: API key as string or SecretStr

        Returns:
            SecretStr: Secured API key
        """
        if isinstance(v, str):
            return SecretStr(v)
        return v

    model_config = ConfigDict(from_attributes=True)
