"""Core configuration settings for RAG Modulo application initialization."""

from typing import Optional, List, Dict
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


class LegacySettings(Settings):
    """Temporary class to maintain backward compatibility during migration.
    
    This class extends the new Settings class to maintain all existing
    functionality while the configuration system is being refactored.
    It will be removed once the migration to the new configuration
    system is complete.
    """
    # Core data settings
    data_dir: Optional[str] = None
    vector_db: str = "None"
    collection_name: Optional[str] = None
    llm_concurrency: int = Field(default=10, env='LLM_CONCURRENCY')

    # Search settings
    number_of_results: int = Field(default=5, env='NUMBER_OF_RESULTS')

    # Chunking settings
    chunking_strategy: str = Field(default="fixed", env='CHUNKING_STRATEGY')
    min_chunk_size: int = Field(default=100, env='MIN_CHUNK_SIZE')
    max_chunk_size: int = Field(default=400, env='MAX_CHUNK_SIZE')
    chunk_overlap: int = Field(default=10, env='CHUNK_OVERLAP')
    semantic_threshold: float = Field(default=0.5, env='SEMANTIC_THRESHOLD')

    # Embedding settings
    embedding_model: str = Field(
        default="sentence-transformers/all-minilm-l6-v2",
        env='EMBEDDING_MODEL'
    )
    embedding_dim: int = Field(default=384, env='EMBEDDING_DIM')
    embedding_field: str = Field(default="embedding", env='EMBEDDING_FIELD')
    upsert_batch_size: int = Field(default=100, env='UPSERT_BATCH_SIZE')

    # LLM settings
    rag_llm: str = Field(..., env='RAG_LLM')
    max_new_tokens: int = Field(default=500, env='MAX_NEW_TOKENS')
    min_new_tokens: int = Field(default=200, env='MIN_NEW_TOKENS')
    max_context_length: int = Field(default=2048, env='MAX_CONTEXT_LENGTH')
    random_seed: int = Field(default=50, env='RANDOM_SEED')
    top_k: int = Field(default=5, env='TOP_K')
    top_p: float = Field(default=0.95, env='TOP_P')
    temperature: float = Field(default=0.7, env='TEMPERATURE')
    repetition_penalty: float = Field(default=1.1, env='REPETITION_PENALTY')
    runtime_eval: bool = Field(default=False, env='RUNTIME_EVAL')

    # Query Rewriting settings
    use_simple_rewriter: bool = Field(default=True, env='USE_SIMPLE_REWRITER')
    use_hyponym_rewriter: bool = Field(default=False, env='USE_HYPONYM_REWRITER')
    rewriter_model: str = Field(
        default="ibm/granite-13b-chat-v2",
        env='REWRITER_MODEL'
    )
    rewriter_temperature: float = Field(default=0.7, env='REWRITER_TEMPERATURE')

    # ... other legacy settings ...

    @classmethod
    def parse_env_var(cls, field_name: str, raw_val: str) -> Any:
        """Parse environment variables, handling lists and special types."""
        if field_name in {"question_types", "question_patterns", "question_required_terms"}:
            if raw_val.startswith("[") and raw_val.endswith("]"):
                return [item.strip(' "\'') for item in raw_val[1:-1].split(",")]
        return raw_val


# Feature flag for new configuration system
USE_NEW_CONFIG = os.getenv('USE_NEW_CONFIG', 'false').lower() == 'true'

# Create appropriate settings instance
settings = Settings() if USE_NEW_CONFIG else LegacySettings()
