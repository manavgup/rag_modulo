"""Core configuration required at application startup."""

import tempfile
from typing import Optional, List, Dict, Any
import os
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    @field_validator('collectiondb_port')
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate port number is in valid range."""
        if not 1 <= v <= 65535:
            raise ValueError('Port must be between 1 and 65535')
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow"
    )


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

    # Retrieval settings
    retrieval_type: str = Field(
        default="vector",
        env='RETRIEVAL_TYPE'
    )
    vector_weight: float = Field(default=0.7, env='VECTOR_WEIGHT')
    keyword_weight: float = Field(default=0.3, env='KEYWORD_WEIGHT')
    hybrid_weight: float = Field(default=0.5, env='HYBRID_WEIGHT')

    # Question suggestion settings
    question_suggestion_num: int = Field(default=3, env='QUESTION_SUGGESTION_NUM')
    question_min_length: int = Field(default=15, env='QUESTION_MIN_LENGTH')
    question_max_length: int = Field(default=150, env='QUESTION_MAX_LENGTH')
    question_temperature: float = Field(default=0.7, env='QUESTION_TEMPERATURE')
    question_types: List[str] = Field(
        default=[
            "What is",
            "How does",
            "Why is",
            "When should",
            "Which factors"
        ],
        env='QUESTION_TYPES'
    )
    question_patterns: List[str] = Field(
        default=[
            "^What",
            "^How",
            "^Why",
            "^When",
            "^Which"
        ],
        env='QUESTION_PATTERNS'
    )
    question_required_terms: List[str] = Field(
        default=[],
        env='QUESTION_REQUIRED_TERMS'
    )

    # Frontend settings
    react_app_api_url: str = Field(default="/api", env='REACT_APP_API_URL')
    frontend_url: str = Field(default="http://localhost:3000", env='FRONTEND_URL')
    frontend_callback: str = "/callback"

    # Logging settings
    log_level: str = Field(default="INFO", env='LOG_LEVEL')

    # File storage path
    file_storage_path: str = Field(default=tempfile.gettempdir(), env='FILE_STORAGE_PATH')

    # Vector Database Credentials
    # ChromaDB
    chromadb_host: Optional[str] = Field(default="localhost", env='CHROMADB_HOST')
    chromadb_port: Optional[int] = Field(default=8000, env='CHROMADB_PORT')

    # Milvus
    milvus_host: Optional[str] = Field(default="localhost", env='MILVUS_HOST')
    milvus_port: Optional[int] = Field(default=19530, env='MILVUS_PORT')
    milvus_user: Optional[str] = Field(default="root", env='MILVUS_USER')
    milvus_password: Optional[str] = Field(default="milvus", env='MILVUS_PASSWORD')
    milvus_index_params: Optional[str] = Field(default=None, env='MILVUS_INDEX_PARAMS')
    milvus_search_params: Optional[str] = Field(default=None, env='MILVUS_SEARCH_PARAMS')

    # Elasticsearch
    elastic_host: Optional[str] = Field(default="localhost", env='ELASTIC_HOST')
    elastic_port: Optional[int] = Field(default=9200, env='ELASTIC_PORT')
    elastic_password: Optional[str] = Field(default=None, env='ELASTIC_PASSWORD')
    elastic_cacert_path: Optional[str] = Field(default=None, env='ELASTIC_CACERT_PATH')
    elastic_cloud_id: Optional[str] = Field(default=None, env='ELASTIC_CLOUD_ID')
    elastic_api_key: Optional[str] = Field(default=None, env='ELASTIC_API_KEY')

    # Pinecone
    pinecone_api_key: Optional[str] = Field(default=None, env='PINECONE_API_KEY')
    pinecone_cloud: Optional[str] = Field(default="aws", env='PINECONE_CLOUD')
    pinecone_region: Optional[str] = Field(default="us-east-1", env='PINECONE_REGION')

    # Weaviate
    weaviate_host: Optional[str] = Field(default="localhost", env='WEAVIATE_HOST')
    weaviate_port: Optional[int] = Field(default=8080, env='WEAVIATE_PORT')
    weaviate_grpc_port: Optional[int] = Field(default=50051, env='WEAVIATE_GRPC_PORT')
    weaviate_username: Optional[str] = Field(default=None, env='WEAVIATE_USERNAME')
    weaviate_password: Optional[str] = Field(default=None, env='WEAVIATE_PASSWORD')
    weaviate_index: Optional[str] = Field(default="default", env='WEAVIATE_INDEX')
    weaviate_scopes: Optional[str] = Field(default=None, env='WEAVIATE_SCOPES')

    # OIDC endpoints
    oidc_discovery_endpoint: Optional[str] = Field(default=None, env='OIDC_DISCOVERY_ENDPOINT')
    oidc_auth_url: Optional[str] = Field(default=None, env='OIDC_AUTH_URL')
    oidc_token_url: Optional[str] = Field(default=None, env='OIDC_TOKEN_URL')
    oidc_userinfo_endpoint: Optional[str] = Field(default=None, env='OIDC_USERINFO_ENDPOINT')
    oidc_introspection_endpoint: Optional[str] = Field(default=None, env='OIDC_INTROSPECTION_ENDPOINT')

    # RBAC settings
    rbac_mapping: Dict[str, Dict[str, List[str]]] = {
        'admin': {
            r'^/api/user-collections/(.+)$': ['GET'],
            r'^/api/user-collections/(.+)/(.+)$': ['POST', 'DELETE'],
        },
        'user': {
            r'^/api/user-collections/(.+)/(.+)$': ['POST', 'DELETE'],
            r'^/api/user-collections/(.+)$': ['GET'],
            r'^/api/user-collections/collection/(.+)$': ['GET'],
            r'^/api/user-collections/collection/(.+)/users$': ['DELETE'],
            r'^/api/collections/(.+)$': ['GET']
        },
        'guest': {
            r'^/api/user-collections$': ['GET', 'POST', 'DELETE', 'PUT'],
            r'^/api/collections$': ['GET', 'POST', 'DELETE', 'PUT'],
            r'^/api/collection/(.+)$': ['GET', 'POST', 'DELETE', 'PUT']
        }
    }

    @model_validator(mode='before')
    @classmethod
    def parse_env_lists(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Parse environment variables, handling lists and special types."""
        for field_name in {"question_types", "question_patterns", "question_required_terms"}:
            if isinstance(values.get(field_name), str):
                raw_val = values[field_name]
                if raw_val.startswith("[") and raw_val.endswith("]"):
                    values[field_name] = [item.strip(' "\'') for item in raw_val[1:-1].split(",")]
        return values


# Feature flag for new configuration system
USE_NEW_CONFIG = os.getenv('USE_NEW_CONFIG', 'false').lower() == 'true'

# Create appropriate settings instance
settings = Settings() if USE_NEW_CONFIG else LegacySettings()