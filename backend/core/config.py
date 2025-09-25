"""Configuration settings for the RAG Modulo application."""

import tempfile
from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic.fields import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from core.logging_utils import get_logger


class Settings(BaseSettings):
    """Application settings with environment variable loading."""

    model_config = SettingsConfigDict(extra="allow", validate_default=True, case_sensitive=False)

    # Required settings with defaults for development/testing
    jwt_secret_key: Annotated[
        str, Field(default="dev-secret-key-change-in-production-f8a7b2c1", alias="JWT_SECRET_KEY")
    ]
    rag_llm: Annotated[str, Field(default="ibm/granite-3-3-8b-instruct", alias="RAG_LLM")]

    # Search settings
    number_of_results: Annotated[int, Field(default=5, alias="NUMBER_OF_RESULTS")]
    runtime_eval: Annotated[bool, Field(default=False, alias="RUNTIME_EVAL")]

    # Core data settings
    data_dir: Annotated[str | None, Field(default=None, alias="DATA_DIR")]
    vector_db: Annotated[str, Field(default="milvus", alias="VECTOR_DB")]
    collection_name: Annotated[str | None, Field(default=None, alias="COLLECTION_NAME")]

    # LLM Provider credentials with defaults
    wx_project_id: Annotated[str, Field(default="", alias="WATSONX_INSTANCE_ID")]
    wx_api_key: Annotated[str, Field(default="", alias="WATSONX_APIKEY")]
    wx_url: Annotated[str, Field(default="https://us-south.ml.cloud.ibm.com", alias="WATSONX_URL")]
    openai_api_key: Annotated[str | None, Field(default=None, alias="OPENAI_API_KEY")]
    anthropic_api_key: Annotated[str | None, Field(default=None, alias="ANTHROPIC_API_KEY")]

    # Chunking settings
    chunking_strategy: Annotated[str, Field(default="fixed", alias="CHUNKING_STRATEGY")]
    min_chunk_size: Annotated[int, Field(default=100, alias="MIN_CHUNK_SIZE")]
    max_chunk_size: Annotated[int, Field(default=400, alias="MAX_CHUNK_SIZE")]
    chunk_overlap: Annotated[int, Field(default=10, alias="CHUNK_OVERLAP")]
    semantic_threshold: Annotated[float, Field(default=0.5, alias="SEMANTIC_THRESHOLD")]

    # Chain of Thought (CoT) settings
    cot_max_reasoning_depth: Annotated[int, Field(default=3, alias="COT_MAX_REASONING_DEPTH")]
    cot_reasoning_strategy: Annotated[str, Field(default="decomposition", alias="COT_REASONING_STRATEGY")]
    cot_token_budget_multiplier: Annotated[float, Field(default=2.0, alias="COT_TOKEN_BUDGET_MULTIPLIER")]

    # Embedding settings
    embedding_model: Annotated[str, Field(default="sentence-transformers/all-minilm-l6-v2", alias="EMBEDDING_MODEL")]
    embedding_dim: Annotated[int, Field(default=384, alias="EMBEDDING_DIM")]
    embedding_field: Annotated[str, Field(default="embedding", alias="EMBEDDING_FIELD")]
    upsert_batch_size: Annotated[int, Field(default=100, alias="UPSERT_BATCH_SIZE")]

    # Embedding configuration - using WatsonX SDK native parameters
    embedding_batch_size: Annotated[int, Field(default=5, alias="EMBEDDING_BATCH_SIZE")]  # Reduced from 10 to 5
    embedding_concurrency_limit: Annotated[int, Field(default=1, alias="EMBEDDING_CONCURRENCY_LIMIT")]
    embedding_max_retries: Annotated[int, Field(default=10, alias="EMBEDDING_MAX_RETRIES")]
    embedding_delay_time: Annotated[
        float, Field(default=1.0, alias="EMBEDDING_DELAY_TIME")
    ]  # Increased from 0.5 to 1.0
    embedding_request_delay: Annotated[
        float, Field(default=0.5, alias="EMBEDDING_REQUEST_DELAY")
    ]  # Increased from 0.2 to 0.5

    # LLM configuration - using WatsonX SDK native parameters
    llm_max_retries: Annotated[int, Field(default=10, alias="LLM_MAX_RETRIES")]
    llm_delay_time: Annotated[float, Field(default=0.5, alias="LLM_DELAY_TIME")]

    # LLM settings
    max_new_tokens: Annotated[int, Field(default=500, alias="MAX_NEW_TOKENS")]
    min_new_tokens: Annotated[int, Field(default=200, alias="MIN_NEW_TOKENS")]
    max_context_length: Annotated[int, Field(default=2048, alias="MAX_CONTEXT_LENGTH")]  # Total context window
    random_seed: Annotated[int, Field(default=50, alias="RANDOM_SEED")]
    top_k: Annotated[int, Field(default=5, alias="TOP_K")]
    top_p: Annotated[float, Field(default=0.95, alias="TOP_P")]
    temperature: Annotated[float, Field(default=0.7, alias="TEMPERATURE")]
    repetition_penalty: Annotated[float, Field(default=1.1, alias="REPETITION_PENALTY")]
    llm_concurrency: Annotated[int, Field(default=8, alias="LLM_CONCURRENCY")]

    # Query Rewriting settings
    use_simple_rewriter: Annotated[bool, Field(default=True, alias="USE_SIMPLE_REWRITER")]
    use_hyponym_rewriter: Annotated[bool, Field(default=False, alias="USE_HYPONYM_REWRITER")]
    rewriter_model: Annotated[str, Field(default="ibm/granite-13b-chat-v2", alias="REWRITER_MODEL")]
    rewriter_temperature: Annotated[float, Field(default=0.7, alias="REWRITER_TEMPERATURE")]

    # Retrieval settings
    retrieval_type: Annotated[str, Field(default="vector", alias="RETRIEVAL_TYPE")]  # Options: vector, keyword, hybrid
    vector_weight: Annotated[float, Field(default=0.7, alias="VECTOR_WEIGHT")]
    keyword_weight: Annotated[float, Field(default=0.3, alias="KEYWORD_WEIGHT")]
    hybrid_weight: Annotated[float, Field(default=0.5, alias="HYBRID_WEIGHT")]

    # Question suggestion settings
    question_suggestion_num: Annotated[int, Field(default=5, alias="QUESTION_SUGGESTION_NUM")]
    question_min_length: Annotated[int, Field(default=15, alias="QUESTION_MIN_LENGTH")]
    question_max_length: Annotated[int, Field(default=150, alias="QUESTION_MAX_LENGTH")]
    question_temperature: Annotated[float, Field(default=0.7, alias="QUESTION_TEMPERATURE")]
    question_types: Annotated[
        list[str],
        Field(default=["What is", "How does", "Why is", "When should", "Which factors"], alias="QUESTION_TYPES"),
    ]
    question_patterns: Annotated[
        list[str], Field(default=["^What", "^How", "^Why", "^When", "^Which"], alias="QUESTION_PATTERNS")
    ]
    question_required_terms: Annotated[list[str], Field(default=[], alias="QUESTION_REQUIRED_TERMS")]

    # Frontend settings
    react_app_api_url: Annotated[str, Field(default="/api", alias="REACT_APP_API_URL")]
    frontend_url: Annotated[str, Field(default="http://localhost:3000", alias="FRONTEND_URL")]
    frontend_callback: Annotated[str, Field(default="/callback", alias="FRONTEND_CALLBACK")]

    # Logging settings
    log_level: Annotated[str, Field(default="INFO", alias="LOG_LEVEL")]

    # Testing settings
    testing: Annotated[bool, Field(default=False, alias="TESTING")]
    skip_auth: Annotated[bool, Field(default=False, alias="SKIP_AUTH")]
    development_mode: Annotated[bool, Field(default=False, alias="DEVELOPMENT_MODE")]
    mock_token: Annotated[str, Field(default="dev-0000-0000-0000", alias="MOCK_TOKEN")]

    # File storage path
    file_storage_path: Annotated[str, Field(default=tempfile.gettempdir(), alias="FILE_STORAGE_PATH")]

    # Vector Database Credentials
    # ChromaDB
    chromadb_host: Annotated[str | None, Field(default="localhost", alias="CHROMADB_HOST")]
    chromadb_port: Annotated[int | None, Field(default=8000, alias="CHROMADB_PORT")]

    # Milvus
    milvus_host: Annotated[str | None, Field(default="localhost", alias="MILVUS_HOST")]
    milvus_port: Annotated[int | None, Field(default=19530, alias="MILVUS_PORT")]
    milvus_user: Annotated[str | None, Field(default="root", alias="MILVUS_USER")]
    milvus_password: Annotated[str | None, Field(default="milvus", alias="MILVUS_PASSWORD")]
    milvus_index_params: Annotated[str | None, Field(default=None, alias="MILVUS_INDEX_PARAMS")]
    milvus_search_params: Annotated[str | None, Field(default=None, alias="MILVUS_SEARCH_PARAMS")]

    # Elasticsearch
    elastic_host: Annotated[str | None, Field(default="localhost", alias="ELASTIC_HOST")]
    elastic_port: Annotated[int | None, Field(default=9200, alias="ELASTIC_PORT")]
    elastic_password: Annotated[str | None, Field(default=None, alias="ELASTIC_PASSWORD")]
    elastic_cacert_path: Annotated[str | None, Field(default=None, alias="ELASTIC_CACERT_PATH")]
    elastic_cloud_id: Annotated[str | None, Field(default=None, alias="ELASTIC_CLOUD_ID")]
    elastic_api_key: Annotated[str | None, Field(default=None, alias="ELASTIC_API_KEY")]

    # Pinecone
    pinecone_api_key: Annotated[str | None, Field(default=None, alias="PINECONE_API_KEY")]
    pinecone_cloud: Annotated[str | None, Field(default="aws", alias="PINECONE_CLOUD")]
    pinecone_region: Annotated[str | None, Field(default="us-east-1", alias="PINECONE_REGION")]

    # Weaviate
    weaviate_host: Annotated[str | None, Field(default="localhost", alias="WEAVIATE_HOST")]
    weaviate_port: Annotated[int | None, Field(default=8080, alias="WEAVIATE_PORT")]
    weaviate_grpc_port: Annotated[int | None, Field(default=50051, alias="WEAVIATE_GRPC_PORT")]
    weaviate_username: Annotated[str | None, Field(default=None, alias="WEAVIATE_USERNAME")]
    weaviate_password: Annotated[str | None, Field(default=None, alias="WEAVIATE_PASSWORD")]
    weaviate_index: Annotated[str | None, Field(default="default", alias="WEAVIATE_INDEX")]
    weaviate_scopes: Annotated[str | None, Field(default=None, alias="WEAVIATE_SCOPES")]

    # Project settings
    project_name: Annotated[str, Field(default="rag_modulo", alias="PROJECT_NAME")]
    python_version: Annotated[str, Field(default="3.11", alias="PYTHON_VERSION")]

    # Collection database settings
    collectiondb_user: Annotated[str, Field(default="rag_user", alias="COLLECTIONDB_USER")]
    collectiondb_pass: Annotated[str, Field(default="rag_password", alias="COLLECTIONDB_PASS")]
    collectiondb_host: Annotated[str, Field(default="localhost", alias="COLLECTIONDB_HOST")]
    collectiondb_port: Annotated[int, Field(default=5432, alias="COLLECTIONDB_PORT")]
    collectiondb_name: Annotated[str, Field(default="rag_modulo", alias="COLLECTIONDB_NAME")]

    # IBM OIDC settings
    ibm_client_id: Annotated[str | None, Field(default=None, alias="IBM_CLIENT_ID")]
    ibm_client_secret: Annotated[str | None, Field(default=None, alias="IBM_CLIENT_SECRET")]
    oidc_discovery_endpoint: Annotated[str | None, Field(default=None, alias="OIDC_DISCOVERY_ENDPOINT")]
    oidc_auth_url: Annotated[str | None, Field(default=None, alias="OIDC_AUTH_URL")]
    oidc_token_url: Annotated[str | None, Field(default=None, alias="OIDC_TOKEN_URL")]
    oidc_userinfo_endpoint: Annotated[str | None, Field(default=None, alias="OIDC_USERINFO_ENDPOINT")]
    oidc_introspection_endpoint: Annotated[str | None, Field(default=None, alias="OIDC_INTROSPECTION_ENDPOINT")]

    # JWT settings
    jwt_algorithm: Annotated[str, Field(default="HS256", alias="JWT_ALGORITHM")]

    # Podcast Feature Configuration (Future Feature)
    # Audio Processing
    audio_sample_rate: Annotated[int, Field(default=44100, alias="AUDIO_SAMPLE_RATE")]
    audio_bitrate: Annotated[int, Field(default=128, alias="AUDIO_BITRATE")]
    audio_format: Annotated[str, Field(default="mp3", alias="AUDIO_FORMAT")]
    audio_channels: Annotated[int, Field(default=2, alias="AUDIO_CHANNELS")]

    # TTS Configuration
    tts_provider: Annotated[str, Field(default="elevenlabs", alias="TTS_PROVIDER")]
    elevenlabs_api_key: Annotated[str | None, Field(default=None, alias="ELEVENLABS_API_KEY")]
    azure_speech_key: Annotated[str | None, Field(default=None, alias="AZURE_SPEECH_KEY")]
    google_tts_credentials_path: Annotated[str | None, Field(default=None, alias="GOOGLE_TTS_CREDENTIALS_PATH")]

    # Multi-modal AI Models
    multimodal_model_provider: Annotated[str, Field(default="openai", alias="MULTIMODAL_MODEL_PROVIDER")]

    # Audio/Video Processing
    max_audio_file_size_mb: Annotated[int, Field(default=100, alias="MAX_AUDIO_FILE_SIZE_MB")]
    max_video_file_size_mb: Annotated[int, Field(default=500, alias="MAX_VIDEO_FILE_SIZE_MB")]
    audio_retention_days: Annotated[int, Field(default=30, alias="AUDIO_RETENTION_DAYS")]
    video_retention_days: Annotated[int, Field(default=7, alias="VIDEO_RETENTION_DAYS")]

    # Streaming Configuration
    streaming_chunk_size: Annotated[int, Field(default=8192, alias="STREAMING_CHUNK_SIZE")]
    streaming_cache_size_mb: Annotated[int, Field(default=100, alias="STREAMING_CACHE_SIZE_MB")]
    streaming_timeout_seconds: Annotated[int, Field(default=30, alias="STREAMING_TIMEOUT_SECONDS")]

    # Evaluation Settings
    evaluation_model: Annotated[str, Field(default="gpt-4-vision-preview", alias="EVALUATION_MODEL")]
    evaluation_timeout_seconds: Annotated[int, Field(default=60, alias="EVALUATION_TIMEOUT_SECONDS")]
    max_concurrent_evaluations: Annotated[int, Field(default=5, alias="MAX_CONCURRENT_EVALUATIONS")]

    # RBAC settings
    rbac_mapping: Annotated[
        dict[str, dict[str, list[str]]],
        Field(
            default={
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
            },
            env="RBAC_MAPPING",
        ),
    ]

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret(cls, v: str | None) -> str | None:
        """Validate JWT secret key and warn if using default in production."""
        if not v or not v.strip():
            try:
                logger = get_logger(__name__)
                logger.warning("⚠️  Empty JWT secret key. Using default for development.")
            except ImportError:
                print("⚠️  Empty JWT secret key. Using default for development.")
            return "dev-secret-key-change-in-production-f8a7b2c1"

        if "dev-secret-key" in v:
            try:
                logger = get_logger(__name__)
                logger.warning("⚠️  Using default JWT secret. Set JWT_SECRET_KEY for production.")
            except ImportError:
                print("⚠️  Using default JWT secret. Set JWT_SECRET_KEY for production.")
        return v

    @field_validator("rag_llm")
    @classmethod
    def validate_rag_llm(cls, v: str) -> str:
        """Validate RAG LLM model name."""
        # Accept any non-empty string as LLM model name
        if not v or not v.strip():
            try:
                logger = get_logger(__name__)
                logger.warning("⚠️  Empty RAG LLM model name. Using default.")
            except ImportError:
                print("⚠️  Empty RAG LLM model name. Using default.")
            return "ibm/granite-3-3-8b-instruct"
        return v.strip()

    def validate_production_settings(self) -> bool:
        """Validate settings for production deployment."""
        warnings = []

        if "dev-secret-key" in self.jwt_secret_key:
            warnings.append("Using default JWT secret key")

        if not self.wx_api_key or self.wx_api_key == "":
            warnings.append("WatsonX API key not configured")

        if warnings:
            try:
                logger = get_logger(__name__)
                logger.warning("⚠️  Production configuration warnings: %s", ", ".join(warnings))
            except ImportError:
                # Fallback to print if logging utils not available
                print(f"⚠️  Production configuration warnings: {', '.join(warnings)}")

        return len(warnings) == 0


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance with lazy initialization.

    This function creates a single, cached instance of Settings that can be
    imported and used throughout the application. The @lru_cache decorator
    ensures that the same instance is returned on subsequent calls.

    Returns:
        Settings: The cached settings instance
    """
    return Settings()  # type: ignore[call-arg]


# DEPRECATED: Direct module-level settings access
# This will be removed in a future version. Use get_settings() with FastAPI dependency injection instead.
# For now, we call get_settings() directly for backward compatibility during migration.
settings = get_settings()
