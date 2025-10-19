"""Configuration settings for the RAG Modulo application."""

import os
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import field_validator
from pydantic.fields import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from core.logging_utils import get_logger

# Calculate project root (two levels up from this file: backend/core/config.py)
PROJECT_ROOT = Path(__file__).parent.parent.parent
ENV_FILE_PATH = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Application settings with environment variable loading."""

    model_config = SettingsConfigDict(
        extra="allow",
        validate_default=True,
        case_sensitive=False,
        env_file=str(ENV_FILE_PATH),  # Load .env from project root
        env_file_encoding="utf-8",
    )

    # Required settings with defaults for development/testing
    jwt_secret_key: Annotated[
        str,
        Field(
            default="dev-secret-key-change-in-production-f8a7b2c1",
            alias="JWT_SECRET_KEY",
        ),
    ]
    rag_llm: Annotated[str, Field(default="ibm/granite-3-3-8b-instruct", alias="RAG_LLM")]

    # Search settings
    number_of_results: Annotated[int, Field(default=5, alias="NUMBER_OF_RESULTS")]
    runtime_eval: Annotated[bool, Field(default=False, alias="RUNTIME_EVAL")]

    # Core data settings
    data_dir: Annotated[str | None, Field(default=None, alias="DATA_DIR")]
    vector_db: Annotated[str, Field(default="milvus", alias="VECTOR_DB")]
    collection_name: Annotated[str | None, Field(default=None, alias="COLLECTION_NAME")]

    # LLM Provider selection and credentials
    llm_provider: Annotated[str, Field(default="watsonx", alias="LLM_PROVIDER")]  # Options: watsonx, openai, anthropic
    wx_project_id: Annotated[str, Field(default="", alias="WATSONX_INSTANCE_ID")]
    wx_api_key: Annotated[str, Field(default="", alias="WATSONX_APIKEY")]
    wx_url: Annotated[str, Field(default="https://us-south.ml.cloud.ibm.com", alias="WATSONX_URL")]
    openai_api_key: Annotated[str | None, Field(default=None, alias="OPENAI_API_KEY")]
    anthropic_api_key: Annotated[str | None, Field(default=None, alias="ANTHROPIC_API_KEY")]

    # Chunking settings
    # Options: sentence (RECOMMENDED), semantic, hierarchical, token, fixed
    # sentence: Conservative char-to-token (2.5:1), targets 200-400 tokens, sentence boundaries, FAST
    # semantic: Embedding-based semantic boundaries (medium speed)
    # hierarchical: Parent-child structure for context (fast)
    # token: Accurate tokenization via WatsonX API (SLOW - avoid)
    # fixed: Simple character-based (fast but risky)
    chunking_strategy: Annotated[str, Field(default="sentence", alias="CHUNKING_STRATEGY")]
    # Values represent TOKENS for sentence/token strategies, CHARACTERS for others
    # For IBM Slate (512 tokens): target 200-400 tokens per chunk
    min_chunk_size: Annotated[int, Field(default=200, alias="MIN_CHUNK_SIZE")]  # min tokens
    max_chunk_size: Annotated[int, Field(default=300, alias="MAX_CHUNK_SIZE")]  # target tokens
    chunk_overlap: Annotated[int, Field(default=40, alias="CHUNK_OVERLAP")]  # overlap tokens (~13%)
    semantic_threshold: Annotated[float, Field(default=0.5, alias="SEMANTIC_THRESHOLD")]

    # Hierarchical chunking settings
    hierarchical_parent_size: Annotated[int, Field(default=1500, alias="HIERARCHICAL_PARENT_SIZE")]
    hierarchical_child_size: Annotated[int, Field(default=300, alias="HIERARCHICAL_CHILD_SIZE")]
    hierarchical_levels: Annotated[int, Field(default=2, alias="HIERARCHICAL_LEVELS")]  # 2 or 3 levels
    hierarchical_strategy: Annotated[
        str, Field(default="size_based", alias="HIERARCHICAL_STRATEGY")
    ]  # Options: size_based, sentence_based
    hierarchical_sentences_per_child: Annotated[int, Field(default=3, alias="HIERARCHICAL_SENTENCES_PER_CHILD")]
    hierarchical_children_per_parent: Annotated[int, Field(default=5, alias="HIERARCHICAL_CHILDREN_PER_PARENT")]
    hierarchical_retrieval_mode: Annotated[
        str, Field(default="child_with_parent", alias="HIERARCHICAL_RETRIEVAL_MODE")
    ]  # Options: child_only, child_with_parent, full_hierarchy

    # IBM Docling Feature Flags
    enable_docling: Annotated[bool, Field(default=False, alias="ENABLE_DOCLING")]
    docling_fallback_enabled: Annotated[bool, Field(default=True, alias="DOCLING_FALLBACK_ENABLED")]

    # Chain of Thought (CoT) settings
    cot_max_reasoning_depth: Annotated[int, Field(default=3, alias="COT_MAX_REASONING_DEPTH")]
    cot_reasoning_strategy: Annotated[str, Field(default="decomposition", alias="COT_REASONING_STRATEGY")]
    cot_token_budget_multiplier: Annotated[float, Field(default=2.0, alias="COT_TOKEN_BUDGET_MULTIPLIER")]

    # Embedding settings
    embedding_model: Annotated[
        str,
        Field(default="sentence-transformers/all-minilm-l6-v2", alias="EMBEDDING_MODEL"),
    ]
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
    max_new_tokens: Annotated[int, Field(default=1024, alias="MAX_NEW_TOKENS")]
    min_new_tokens: Annotated[int, Field(default=100, alias="MIN_NEW_TOKENS")]
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

    # Reranking settings
    enable_reranking: Annotated[bool, Field(default=True, alias="ENABLE_RERANKING")]
    reranker_type: Annotated[str, Field(default="llm", alias="RERANKER_TYPE")]  # Options: llm, simple
    reranker_top_k: Annotated[int | None, Field(default=None, alias="RERANKER_TOP_K")]  # None = rerank all results
    reranker_batch_size: Annotated[int, Field(default=10, alias="RERANKER_BATCH_SIZE")]
    reranker_score_scale: Annotated[int, Field(default=10, alias="RERANKER_SCORE_SCALE")]  # 0-10 scoring scale
    reranker_prompt_template_name: Annotated[
        str, Field(default="reranking", alias="RERANKER_PROMPT_TEMPLATE_NAME")
    ]  # Template name for reranking prompts

    # Podcast Generation settings
    # Environment: "development" uses FastAPI BackgroundTasks + local filesystem
    #              "production" uses Celery + MinIO/S3
    podcast_environment: Annotated[str, Field(default="development", alias="PODCAST_ENVIRONMENT")]

    # Background task processing
    podcast_task_backend: Annotated[
        str, Field(default="fastapi", alias="PODCAST_TASK_BACKEND")
    ]  # Options: fastapi, celery
    celery_broker_url: Annotated[str | None, Field(default=None, alias="CELERY_BROKER_URL")]
    celery_result_backend: Annotated[str | None, Field(default=None, alias="CELERY_RESULT_BACKEND")]

    # Storage backend
    podcast_storage_backend: Annotated[
        str, Field(default="local", alias="PODCAST_STORAGE_BACKEND")
    ]  # Options: local, minio, s3, r2

    # Local filesystem storage (development)
    # Use absolute path to avoid working directory issues
    # Default is relative to backend directory: backend/data/podcasts
    podcast_local_storage_path: Annotated[
        str,
        Field(
            default="data/podcasts",  # Will be resolved to absolute path in __init__
            alias="PODCAST_LOCAL_STORAGE_PATH",
        ),
    ]

    # MinIO/S3 storage (production)
    podcast_minio_endpoint: Annotated[str | None, Field(default=None, alias="PODCAST_MINIO_ENDPOINT")]
    podcast_minio_access_key: Annotated[str | None, Field(default=None, alias="PODCAST_MINIO_ACCESS_KEY")]
    podcast_minio_secret_key: Annotated[str | None, Field(default=None, alias="PODCAST_MINIO_SECRET_KEY")]
    podcast_minio_bucket: Annotated[str, Field(default="rag-modulo-podcasts", alias="PODCAST_MINIO_BUCKET")]
    podcast_minio_region: Annotated[str, Field(default="us-east-1", alias="PODCAST_MINIO_REGION")]

    # Audio generation provider
    podcast_audio_provider: Annotated[
        str, Field(default="openai", alias="PODCAST_AUDIO_PROVIDER")
    ]  # Options: openai, watsonx
    podcast_fallback_audio_provider: Annotated[
        str | None, Field(default=None, alias="PODCAST_FALLBACK_AUDIO_PROVIDER")
    ]  # Optional fallback

    # OpenAI TTS settings
    openai_tts_model: Annotated[str, Field(default="tts-1-hd", alias="OPENAI_TTS_MODEL")]  # or "tts-1" for faster
    openai_tts_default_voice: Annotated[
        str, Field(default="alloy", alias="OPENAI_TTS_DEFAULT_VOICE")
    ]  # alloy, echo, fable, onyx, nova, shimmer

    # WatsonX TTS settings (fallback)
    watsonx_tts_api_key: Annotated[str | None, Field(default=None, alias="WATSONX_TTS_API_KEY")]
    watsonx_tts_url: Annotated[
        str | None,
        Field(
            default="https://api.us-south.text-to-speech.watson.cloud.ibm.com",
            alias="WATSONX_TTS_URL",
        ),
    ]
    watsonx_tts_default_voice: Annotated[str, Field(default="en-US_AllisonV3Voice", alias="WATSONX_TTS_DEFAULT_VOICE")]

    # Podcast validation and limits
    podcast_min_documents: Annotated[int, Field(default=1, alias="PODCAST_MIN_DOCUMENTS")]
    podcast_max_concurrent_per_user: Annotated[int, Field(default=3, alias="PODCAST_MAX_CONCURRENT_PER_USER")]
    podcast_url_expiry_days: Annotated[int, Field(default=7, alias="PODCAST_URL_EXPIRY_DAYS")]

    # Content retrieval for podcasts
    podcast_retrieval_top_k_short: Annotated[int, Field(default=30, alias="PODCAST_RETRIEVAL_TOP_K_SHORT")]  # 5 min
    podcast_retrieval_top_k_medium: Annotated[int, Field(default=50, alias="PODCAST_RETRIEVAL_TOP_K_MEDIUM")]  # 15 min
    podcast_retrieval_top_k_long: Annotated[int, Field(default=75, alias="PODCAST_RETRIEVAL_TOP_K_LONG")]  # 30 min
    podcast_retrieval_top_k_extended: Annotated[
        int, Field(default=100, alias="PODCAST_RETRIEVAL_TOP_K_EXTENDED")
    ]  # 60 min

    # Question suggestion settings
    question_suggestion_num: Annotated[int, Field(default=5, alias="QUESTION_SUGGESTION_NUM")]
    question_min_length: Annotated[int, Field(default=15, alias="QUESTION_MIN_LENGTH")]
    question_max_length: Annotated[int, Field(default=150, alias="QUESTION_MAX_LENGTH")]
    question_temperature: Annotated[float, Field(default=0.7, alias="QUESTION_TEMPERATURE")]
    question_types: Annotated[
        list[str],
        Field(
            default=["What is", "How does", "Why is", "When should", "Which factors"],
            alias="QUESTION_TYPES",
        ),
    ]
    question_patterns: Annotated[
        list[str],
        Field(
            default=["^What", "^How", "^Why", "^When", "^Which"],
            alias="QUESTION_PATTERNS",
        ),
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
    # Note: mock_token removed - now hardcoded as BYPASS_TOKEN in auth_router.py
    mock_user_email: Annotated[str, Field(default="dev@example.com", alias="MOCK_USER_EMAIL")]
    mock_user_name: Annotated[str, Field(default="Development User", alias="MOCK_USER_NAME")]

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
    collectiondb_user: Annotated[str, Field(default="rag_modulo_user", alias="COLLECTIONDB_USER")]
    collectiondb_pass: Annotated[str, Field(default="rag_modulo_password", alias="COLLECTIONDB_PASS")]
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
                    r"^/api/users/(.+)/llm-providers.*$": [
                        "GET",
                        "POST",
                        "PUT",
                        "DELETE",
                    ],
                    r"^/api/users/(.+)/llm-parameters.*$": [
                        "GET",
                        "POST",
                        "PUT",
                        "DELETE",
                    ],
                    r"^/api/users/(.+)/prompt-templates.*$": [
                        "GET",
                        "POST",
                        "PUT",
                        "DELETE",
                    ],
                    r"^/api/users/(.+)/pipelines.*$": ["GET", "POST", "PUT", "DELETE"],
                    r"^/api/users/(.+)/collections.*$": [
                        "GET",
                        "POST",
                        "PUT",
                        "DELETE",
                    ],
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
        if v and "dev-secret-key" in v and os.getenv("ENVIRONMENT", "").lower() in ("production", "prod"):
            try:
                logger = get_logger(__name__)
                logger.warning("⚠️  Using default JWT secret in production! Set JWT_SECRET_KEY environment variable.")
            except ImportError:
                # Fallback to print if logging utils not available
                print("⚠️  Using default JWT secret in production! Set JWT_SECRET_KEY environment variable.")
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

    @field_validator("file_storage_path")
    @classmethod
    def validate_file_storage_path(cls, v: str) -> str:
        """Validate and resolve file storage path to absolute path.

        Resolves relative paths (e.g., ./data/files) to absolute paths
        based on the project root directory. Creates the directory if
        it doesn't exist.

        Args:
            v: The file storage path from environment or default

        Returns:
            str: Absolute path to the file storage directory
        """
        from pathlib import Path

        # Convert to Path object
        path = Path(v)

        # If path is relative, resolve it relative to project root
        if not path.is_absolute():
            # Get the directory containing this config.py file (backend/core)
            config_dir = Path(__file__).parent
            # Go up to backend directory, then to project root
            project_root = config_dir.parent.parent
            # Resolve the path relative to project root
            path = (project_root / path).resolve()

        # Create directory if it doesn't exist
        path.mkdir(parents=True, exist_ok=True)

        return str(path)

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
    return Settings()


# DEPRECATED: Direct module-level settings access
# This will be removed in a future version. Use get_settings() with FastAPI dependency injection instead.
# For now, we call get_settings() directly for backward compatibility during migration.
settings = get_settings()
