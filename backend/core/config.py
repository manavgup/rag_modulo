"""Configuration settings for the RAG Modulo application."""

import tempfile
from typing import Optional, List, Dict, Any
import os
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables with defaults."""

    # WatsonX.ai credentials
    wx_project_id: Optional[str] = Field(default_factory=lambda: os.getenv('WATSONX_INSTANCE_ID', None))
    wx_api_key: Optional[str] = Field(default_factory=lambda: os.getenv('WATSONX_APIKEY', None))
    wx_url: Optional[str] = Field(default_factory=lambda: os.getenv('WATSONX_URL', None))

    # Core data settings
    data_dir: Optional[str] = None
    vector_db: str = "None"
    collection_name: Optional[str] = None

    # Chunking settings
    chunking_strategy: str = Field(default="fixed", env='CHUNKING_STRATEGY')
    min_chunk_size: int = Field(default=100, env='MIN_CHUNK_SIZE')
    max_chunk_size: int = Field(default=400, env='MAX_CHUNK_SIZE')
    chunk_overlap: int = Field(default=10, env='CHUNK_OVERLAP')
    semantic_threshold: float = Field(default=0.5, env='SEMANTIC_THRESHOLD')

    # Embedding settings
    embedding_model: str = Field(default="sentence-transformers/all-minilm-l6-v2", env='EMBEDDING_MODEL')
    embedding_dim: int = Field(default=384, env='EMBEDDING_DIM')
    embedding_field: str = Field(default="embedding", env='EMBEDDING_FIELD')
    upsert_batch_size: int = Field(default=100, env='UPSERT_BATCH_SIZE')

    # LLM settings
    rag_llm: str = Field(..., env='RAG_LLM')
    max_new_tokens: int = Field(default=500, env='MAX_NEW_TOKENS')
    min_new_tokens: int = Field(default=200, env='MIN_NEW_TOKENS')
    random_seed: int = Field(default=50, env='RANDOM_SEED')
    top_k: int = Field(default=5, env='TOP_K')
    top_p: float = Field(default=0.95, env='TOP_P')
    temperature: float = Field(default=0.7, env='TEMPERATURE')
    repetition_penalty: float = Field(default=1.1, env='REPETITION_PENALTY')

    # Query Rewriting settings
    use_simple_rewriter: bool = Field(default=True, env='USE_SIMPLE_REWRITER')
    use_hyponym_rewriter: bool = Field(default=False, env='USE_HYPONYM_REWRITER')
    rewriter_model: str = Field(default="ibm/granite-13b-chat-v2", env='REWRITER_MODEL')
    rewriter_temperature: float = Field(default=0.7, env='REWRITER_TEMPERATURE')

    # Retrieval settings
    retrieval_type: str = Field(default="vector", env='RETRIEVAL_TYPE')  # Options: vector, keyword, hybrid
    vector_weight: float = Field(default=0.7, env='VECTOR_WEIGHT')
    keyword_weight: float = Field(default=0.3, env='KEYWORD_WEIGHT')
    hybrid_weight: float = Field(default=0.5, env='HYBRID_WEIGHT')

    # Question suggestion settings
    question_suggestion_num: int = Field(default=5, env='QUESTION_SUGGESTION_NUM')
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

    # File storage settings
    file_storage_path: str = Field(default_factory=lambda: tempfile.gettempdir())

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

    # Project settings
    project_name: str = Field(default="rag_modulo", env='PROJECT_NAME')
    python_version: str = Field(default="3.11", env='PYTHON_VERSION')

    # Collection database settings
    collectiondb_user: str = Field(default="rag_modulo_user", env='COLLECTIONDB_USER')
    collectiondb_pass: str = Field(default="rag_modulo_password", env='COLLECTIONDB_PASS')
    collectiondb_host: str = Field(default="localhost", env='COLLECTIONDB_HOST')
    collectiondb_port: int = Field(default=5432, env='COLLECTIONDB_PORT')
    collectiondb_name: str = Field(default="rag_modulo", env='COLLECTIONDB_NAME')

    # IBM OIDC settings
    ibm_client_id: Optional[str] = Field(default=None, env='IBM_CLIENT_ID')
    ibm_client_secret: Optional[str] = Field(default=None, env='IBM_CLIENT_SECRET')
    oidc_discovery_endpoint: Optional[str] = Field(default=None, env='OIDC_DISCOVERY_ENDPOINT')
    oidc_auth_url: Optional[str] = Field(default=None, env='OIDC_AUTH_URL')
    oidc_token_url: Optional[str] = Field(default=None, env='OIDC_TOKEN_URL')
    oidc_userinfo_endpoint: Optional[str] = Field(default=None, env='OIDC_USERINFO_ENDPOINT')
    oidc_introspection_endpoint: Optional[str] = Field(default=None, env='OIDC_INTROSPECTION_ENDPOINT')

    # JWT settings
    jwt_secret_key: str = Field(..., env='JWT_SECRET_KEY')
    jwt_algorithm: str = "HS256"

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

    class Config:
        """Pydantic config class."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"
        
        @classmethod
        def parse_env_var(cls, field_name: str, raw_val: str) -> Any:
            """Parse environment variables, handling lists and special types."""
            if field_name in {"question_types", "question_patterns", "question_required_terms"}:
                if raw_val.startswith("[") and raw_val.endswith("]"):
                    return [item.strip(' "\'') for item in raw_val[1:-1].split(",")]
            return raw_val


# Create settings instance
settings = Settings()