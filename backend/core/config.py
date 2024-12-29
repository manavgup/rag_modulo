"""Core configuration settings for RAG Modulo application initialization."""

from typing import Optional
import os
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Core application settings required at startup.
    
    This class contains only the essential configuration settings needed
    for application initialization. All other settings are managed through
    the runtime configuration system.
    """

    # WatsonX.ai credentials
    wx_project_id: Optional[str] = Field(
        default=None, 
        env='WATSONX_INSTANCE_ID',
        description="WatsonX instance ID"
    )
    wx_api_key: Optional[str] = Field(
        default=None, 
        env='WATSONX_APIKEY',
        description="WatsonX API key"
    )
    wx_url: Optional[str] = Field(
        default=None, 
        env='WATSONX_URL',
        description="WatsonX base URL"
    )

    # IBM OIDC settings
    ibm_client_id: Optional[str] = Field(
        default=None, 
        env='IBM_CLIENT_ID',
        description="IBM OIDC client ID"
    )
    ibm_client_secret: Optional[str] = Field(
        default=None, 
        env='IBM_CLIENT_SECRET',
        description="IBM OIDC client secret"
    )

    # Collection database settings
    collectiondb_user: str = Field(
        default="rag_modulo_user", 
        env='COLLECTIONDB_USER',
        description="Database username"
    )
    collectiondb_pass: str = Field(
        default="rag_modulo_password", 
        env='COLLECTIONDB_PASS',
        description="Database password"
    )
    collectiondb_host: str = Field(
        default="localhost", 
        env='COLLECTIONDB_HOST',
        description="Database host"
    )
    collectiondb_port: int = Field(
        default=5432, 
        env='COLLECTIONDB_PORT',
        description="Database port"
    )
    collectiondb_name: str = Field(
        default="rag_modulo", 
        env='COLLECTIONDB_NAME',
        description="Database name"
    )

    # Security settings
    jwt_secret_key: str = Field(
        ..., 
        env='JWT_SECRET_KEY',
        description="Secret key for JWT token generation"
    )
    jwt_algorithm: str = "HS256"

    @validator('collectiondb_port')
    def validate_port(cls, v):
        """Validate port number is in valid range."""
        if not 1 <= v <= 65535:
            raise ValueError('Port must be between 1 and 65535')
        return v

    class Config:
        """Pydantic config settings."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"


# Create settings instance
settings = Settings()
