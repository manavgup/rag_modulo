"""Configuration settings for the RAG Modulo application."""

import tempfile
from typing import Annotated

from pydantic.fields import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable loading."""

    model_config = SettingsConfigDict(extra="allow", validate_default=True)

    # Required settings
    jwt_secret_key: str
    rag_llm: str

    # Search settings
    number_of_results: Annotated[int, Field(default=5, env="NUMBER_OF_RESULTS")]
    runtime_eval: Annotated[bool, Field(default=False, env="RUNTIME_EVAL")]

    # Core data settings
    data_dir: str | None = None
    vector_db: Annotated[str, Field(default="milvus", env="VECTOR_DB")]
    collection_name: str | None = None

    # LLM Provider credentials
    wx_project_id: str = Field(alias="WATSONX_INSTANCE_ID")
    wx_api_key: str = Field(alias="WATSONX_APIKEY")
    wx_url: str = Field(alias="WATSONX_URL")
    openai_api_key: Annotated[str | None, Field(default=None, env="OPENAI_API_KEY")]
    anthropic_api_key: Annotated[str | None, Field(default=None, env="ANTHROPIC_API_KEY")]

    # Chunking settings
    chunking_strategy: Annotated[str, Field(default="fixed", env="CHUNKING_STRATEGY")]
    min_chunk_size: Annotated[int, Field(default=100, env="MIN_CHUNK_SIZE")]
    max_chunk_size: Annotated[int, Field(default=400, env="MAX_CHUNK_SIZE")]
    chunk_overlap: Annotated[int, Field(default=10, env="CHUNK_OVERLAP")]
    semantic_threshold: Annotated[float, Field(default=0.5, env="SEMANTIC_THRESHOLD")]

    # Embedding settings
    embedding_model: Annotated[str, Field(default="sentence-transformers/all-minilm-l6-v2", env="EMBEDDING_MODEL")]
    embedding_dim: Annotated[int, Field(default=384, env="EMBEDDING_DIM")]
    embedding_field: Annotated[str, Field(default="embedding", env="EMBEDDING_FIELD")]
    upsert_batch_size: Annotated[int, Field(default=100, env="UPSERT_BATCH_SIZE")]

    # LLM settings
    max_new_tokens: Annotated[int, Field(default=500, env="MAX_NEW_TOKENS")]
    min_new_tokens: Annotated[int, Field(default=200, env="MIN_NEW_TOKENS")]
    max_context_length: Annotated[int, Field(default=2048, env="MAX_CONTEXT_LENGTH")]  # Total context window
    random_seed: Annotated[int, Field(default=50, env="RANDOM_SEED")]
    top_k: Annotated[int, Field(default=5, env="TOP_K")]
    top_p: Annotated[float, Field(default=0.95, env="TOP_P")]
    temperature: Annotated[float, Field(default=0.7, env="TEMPERATURE")]
    repetition_penalty: Annotated[float, Field(default=1.1, env="REPETITION_PENALTY")]
    llm_concurrency: Annotated[int, Field(default=10, env="LLM_CONCURRENCY")]

    # Query Rewriting settings
    use_simple_rewriter: bool = Field(default=True)
    use_hyponym_rewriter: bool = Field(default=False)
    rewriter_model: str = Field(default="ibm/granite-13b-chat-v2")
    rewriter_temperature: float = Field(default=0.7)

    # Retrieval settings
    retrieval_type: str = Field(default="vector")  # Options: vector, keyword, hybrid
    vector_weight: float = Field(default=0.7)
    keyword_weight: float = Field(default=0.3)
    hybrid_weight: float = Field(default=0.5)

    # Question suggestion settings
    question_suggestion_num: int = Field(default=5)
    question_min_length: int = Field(default=15)
    question_max_length: int = Field(default=150)
    question_temperature: float = Field(default=0.7)
    question_types: list[str] = Field(default=["What is", "How does", "Why is", "When should", "Which factors"])
    question_patterns: list[str] = Field(default=["^What", "^How", "^Why", "^When", "^Which"])
    question_required_terms: list[str] = Field(default=[])

    # Frontend settings
    react_app_api_url: Annotated[str, Field(default="/api", env="REACT_APP_API_URL")]
    frontend_url: Annotated[str, Field(default="http://localhost:3000", env="FRONTEND_URL")]
    frontend_callback: str = "/callback"

    # Logging settings
    log_level: Annotated[str, Field(default="INFO", env="LOG_LEVEL")]

    # File storage path
    file_storage_path: Annotated[str, Field(default=tempfile.gettempdir(), env="FILE_STORAGE_PATH")]

    # Vector Database Credentials
    # ChromaDB
    chromadb_host: Annotated[str | None, Field(default="localhost", env="CHROMADB_HOST")]
    chromadb_port: Annotated[int | None, Field(default=8000, env="CHROMADB_PORT")]

    # Milvus
    milvus_host: Annotated[str | None, Field(default="localhost", env="MILVUS_HOST")]
    milvus_port: Annotated[int | None, Field(default=19530, env="MILVUS_PORT")]
    milvus_user: Annotated[str | None, Field(default="root", env="MILVUS_USER")]
    milvus_password: Annotated[str | None, Field(default="milvus", env="MILVUS_PASSWORD")]
    milvus_index_params: Annotated[str | None, Field(default=None, env="MILVUS_INDEX_PARAMS")]
    milvus_search_params: Annotated[str | None, Field(default=None, env="MILVUS_SEARCH_PARAMS")]

    # Elasticsearch
    elastic_host: Annotated[str | None, Field(default="localhost", env="ELASTIC_HOST")]
    elastic_port: Annotated[int | None, Field(default=9200, env="ELASTIC_PORT")]
    elastic_password: Annotated[str | None, Field(default=None, env="ELASTIC_PASSWORD")]
    elastic_cacert_path: Annotated[str | None, Field(default=None, env="ELASTIC_CACERT_PATH")]
    elastic_cloud_id: Annotated[str | None, Field(default=None, env="ELASTIC_CLOUD_ID")]
    elastic_api_key: Annotated[str | None, Field(default=None, env="ELASTIC_API_KEY")]

    # Pinecone
    pinecone_api_key: Annotated[str | None, Field(default=None, env="PINECONE_API_KEY")]
    pinecone_cloud: Annotated[str | None, Field(default="aws", env="PINECONE_CLOUD")]
    pinecone_region: Annotated[str | None, Field(default="us-east-1", env="PINECONE_REGION")]

    # Weaviate
    weaviate_host: Annotated[str | None, Field(default="localhost", env="WEAVIATE_HOST")]
    weaviate_port: Annotated[int | None, Field(default=8080, env="WEAVIATE_PORT")]
    weaviate_grpc_port: Annotated[int | None, Field(default=50051, env="WEAVIATE_GRPC_PORT")]
    weaviate_username: Annotated[str | None, Field(default=None, env="WEAVIATE_USERNAME")]
    weaviate_password: Annotated[str | None, Field(default=None, env="WEAVIATE_PASSWORD")]
    weaviate_index: Annotated[str | None, Field(default="default", env="WEAVIATE_INDEX")]
    weaviate_scopes: Annotated[str | None, Field(default=None, env="WEAVIATE_SCOPES")]

    # Project settings
    project_name: Annotated[str, Field(default="rag_modulo", env="PROJECT_NAME")]
    python_version: Annotated[str, Field(default="3.11", env="PYTHON_VERSION")]

    # Collection database settings
    collectiondb_user: Annotated[str, Field(default="rag_modulo_user", env="COLLECTIONDB_USER")]
    collectiondb_pass: Annotated[str, Field(default="rag_modulo_password", env="COLLECTIONDB_PASS")]
    collectiondb_host: Annotated[str, Field(default="localhost", env="COLLECTIONDB_HOST")]
    collectiondb_port: Annotated[int, Field(default=5432, env="COLLECTIONDB_PORT")]
    collectiondb_name: Annotated[str, Field(default="rag_modulo", env="COLLECTIONDB_NAME")]

    # IBM OIDC settings
    ibm_client_id: Annotated[str | None, Field(default=None, env="IBM_CLIENT_ID")]
    ibm_client_secret: Annotated[str | None, Field(default=None, env="IBM_CLIENT_SECRET")]
    oidc_discovery_endpoint: Annotated[str | None, Field(default=None, env="OIDC_DISCOVERY_ENDPOINT")]
    oidc_auth_url: Annotated[str | None, Field(default=None, env="OIDC_AUTH_URL")]
    oidc_token_url: Annotated[str | None, Field(default=None, env="OIDC_TOKEN_URL")]
    oidc_userinfo_endpoint: Annotated[str | None, Field(default=None, env="OIDC_USERINFO_ENDPOINT")]
    oidc_introspection_endpoint: Annotated[str | None, Field(default=None, env="OIDC_INTROSPECTION_ENDPOINT")]

    # JWT settings
    jwt_algorithm: str = "HS256"

    # RBAC settings
    rbac_mapping: dict[str, dict[str, list[str]]] = {
        "admin": {
            r"^/api/user-collections/(.+)$": ["GET"],
            r"^/api/user-collections/(.+)/(.+)$": ["POST", "DELETE"],
            r"^/api/users/(.+)/.*$": ["GET", "POST", "PUT", "DELETE"],
            r"^/api/collections/(.+)$": ["GET", "POST", "PUT", "DELETE"],
        },
        "user": {
            r"^/api/user-collections/(.+)/(.+)$": ["POST", "DELETE"],
            r"^/api/user-collections/(.+)$": ["GET"],
            r"^/api/user-collections/collection/(.+)$": ["GET"],
            r"^/api/user-collections/collection/(.+)/users$": ["DELETE"],
            r"^/api/collections/(.+)$": ["GET"],
            r"^/api/users/(.+)/llm-providers.*$": ["GET", "POST", "PUT", "DELETE"],
            r"^/api/users/(.+)/llm-parameters.*$": ["GET", "POST", "PUT", "DELETE"],
            r"^/api/users/(.+)/prompt-templates.*$": ["GET", "POST", "PUT", "DELETE"],
            r"^/api/users/(.+)/pipelines.*$": ["GET", "POST", "PUT", "DELETE"],
            r"^/api/users/(.+)/collections.*$": ["GET", "POST", "PUT", "DELETE"],
        },
        "guest": {
            r"^/api/user-collections$": ["GET", "POST", "DELETE", "PUT"],
            r"^/api/collections$": ["GET", "POST", "DELETE", "PUT"],
            r"^/api/collection/(.+)$": ["GET", "POST", "DELETE", "PUT"],
        },
    }


# Singleton for settings
settings = Settings()
