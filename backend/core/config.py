import tempfile
from typing import Optional
import os
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # BAM credentials
    wx_project_id: Optional[str] = Field(default_factory=lambda: os.getenv('WATSONX_INSTANCE_ID', None))
    wx_api_key: Optional[str] = Field(default_factory=lambda: os.getenv('WATSONX_APIKEY', None))
    wx_url: Optional[str] = Field(default_factory=lambda: os.getenv('WATSONX_URL', None))

    # Data Directory
    data_dir: Optional[str] = None

    # VectorDB settings
    vector_db: str = "None"

    # Default collection name
    collection_name: Optional[str] = None

    # Chunking strategy and parameters
    chunking_strategy: Optional[str] = None
    min_chunk_size: Optional[int] = None
    max_chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    semantic_threshold: Optional[float] = None

    # Embedding settings
    embedding_model: Optional[str] = None
    embedding_dim: Optional[int] = None
    embedding_field: Optional[str] = None
    upsert_batch_size: Optional[int] = None

    # LLM settings
    rag_llm: str = Field(..., env='RAG_LLM')
    max_new_tokens: int = Field(..., env='MAX_NEW_TOKENS')
    min_new_tokens: int = Field(..., env='MIN_NEW_TOKENS')
    random_seed: int = Field(..., env='RANDOM_SEED')
    top_k: int = Field(..., env='TOP_K')
    temperature: float = Field(..., env='TEMPERATURE')

    # Frontend settings
    react_app_api_url: str = Field(default="/api", env='REACT_APP_API_URL')

    # Logging Level
    log_level: Optional[str] = None

    # File storage path
    file_storage_path: str = tempfile.gettempdir()

    # ChromaDB credentials
    chromadb_host: Optional[str] = None
    chromadb_port: Optional[int] = None

    # Milvus credentials
    milvus_host: Optional[str] = None
    milvus_port: Optional[int] = None
    milvus_user: Optional[str] = None
    milvus_password: Optional[str] = None
    milvus_index_params: Optional[str] = None
    milvus_search_params: Optional[str] = None

    # Elasticsearch credentials
    elastic_host: Optional[str] = None
    elastic_port: Optional[int] = None
    elastic_password: Optional[str] = None
    elastic_cacert_path: Optional[str] = None
    elastic_cloud_id: Optional[str] = None
    elastic_api_key: Optional[str] = None

    # Pinecone credentials
    pinecone_api_key: Optional[str] = None
    pinecone_cloud: Optional[str] = None
    pinecone_region: Optional[str] = None

    # Weaviate credentials
    weaviate_host: Optional[str] = None
    weaviate_port: Optional[int] = None
    weaviate_grpc_port: Optional[int] = None
    weaviate_username: Optional[str] = None
    weaviate_password: Optional[str] = None
    weaviate_index: Optional[str] = None
    weaviate_scopes: Optional[str] = None

    # Project settings
    project_name: Optional[str] = None
    python_version: Optional[str] = None

    # Collection database settings
    collectiondb_user: Optional[str] = None
    collectiondb_pass: Optional[str] = None
    collectiondb_host: Optional[str] = None
    collectiondb_port: Optional[int] = None
    collectiondb_name: Optional[str] = None

    # IBM OIDC settings
    ibm_client_id: Optional[str] = None
    ibm_client_secret: Optional[str] = None
    oidc_discovery_endpoint: Optional[str] = None
    oidc_auth_url: Optional[str] = None
    oidc_token_url: Optional[str] = None
    frontend_url: str = Field(default="http://localhost:3000", env='FRONTEND_URL')
    oidc_userinfo_endpoint: Optional[str] = None
    oidc_introspection_endpoint: Optional[str] = None

    # JWT settings
    jwt_secret_key: str = Field(..., env='JWT_SECRET_KEY')
    jwt_algorithm: str = "HS256"
    frontend_callback: str = "/callback"
    
    # Role settings
    # This is a sample RBAC mapping role / url_patterns / http_methods
    rbac_mapping: dict = {
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
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"

settings = Settings()
