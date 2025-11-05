"""Settings API router for runtime-safe configuration viewing.

This router provides read-only access to application settings that are
safe to display in the UI. Sensitive values (API keys, secrets) are masked.

Note: These settings come from .env and require application restart to change.
For runtime-changeable configuration, use RuntimeConfig API instead.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from core.config import Settings, get_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


class LLMSettings(BaseModel):
    """LLM configuration settings."""

    max_new_tokens: int = Field(..., description="Maximum tokens to generate")
    min_new_tokens: int = Field(..., description="Minimum tokens to generate")
    temperature: float = Field(..., description="Sampling temperature (0.0-2.0)")
    top_k: int = Field(..., description="Top-K sampling parameter")
    top_p: float = Field(..., description="Top-P (nucleus) sampling parameter")
    repetition_penalty: float = Field(..., description="Repetition penalty")
    llm_provider: str = Field(..., description="Default LLM provider")
    rag_llm: str = Field(..., description="RAG LLM model identifier")


class ChunkingSettings(BaseModel):
    """Chunking configuration settings."""

    chunking_strategy: str = Field(..., description="Chunking strategy")
    min_chunk_size: int = Field(..., description="Minimum chunk size")
    max_chunk_size: int = Field(..., description="Maximum chunk size")
    chunk_overlap: int = Field(..., description="Chunk overlap")
    semantic_threshold: float = Field(..., description="Semantic similarity threshold")


class RetrievalSettings(BaseModel):
    """Retrieval configuration settings."""

    retrieval_type: str = Field(..., description="Retrieval type (vector/keyword/hybrid)")
    number_of_results: int = Field(..., description="Default number of results")
    vector_weight: float = Field(..., description="Vector search weight")
    keyword_weight: float = Field(..., description="Keyword search weight")
    enable_reranking: bool = Field(..., description="Enable reranking")
    reranker_type: str = Field(..., description="Reranker type")
    reranker_top_k: int | None = Field(..., description="Reranker top-K")


class EmbeddingSettings(BaseModel):
    """Embedding configuration settings."""

    embedding_model: str = Field(..., description="Embedding model identifier")
    embedding_dim: int = Field(..., description="Embedding dimensions")
    embedding_batch_size: int = Field(..., description="Embedding batch size")
    embedding_concurrency_limit: int = Field(..., description="Max concurrent embeddings")


class CoTSettings(BaseModel):
    """Chain of Thought configuration settings."""

    cot_max_reasoning_depth: int = Field(..., description="Max reasoning depth")
    cot_reasoning_strategy: str = Field(..., description="Reasoning strategy")
    cot_token_budget_multiplier: float = Field(..., description="Token budget multiplier")


class SystemSettings(BaseModel):
    """System-wide configuration settings (runtime-safe view)."""

    llm: LLMSettings
    chunking: ChunkingSettings
    retrieval: RetrievalSettings
    embedding: EmbeddingSettings
    cot: CoTSettings
    vector_db: str = Field(..., description="Vector database type")
    log_level: str = Field(..., description="Logging level")


@router.get("/", response_model=SystemSettings)
async def get_system_settings(
    settings: Settings = Depends(get_settings),
) -> SystemSettings:
    """Get runtime-safe system settings.

    Returns current application settings from .env configuration.
    Sensitive values (API keys, secrets) are excluded from this response.

    Note:
        - These settings are READ-ONLY via API
        - Changes require updating .env and restarting the application
        - For runtime-changeable config, use /api/runtime-config instead

    Returns:
        SystemSettings: Current application configuration
    """
    return SystemSettings(
        llm=LLMSettings(
            max_new_tokens=settings.max_new_tokens,
            min_new_tokens=settings.min_new_tokens,
            temperature=settings.temperature,
            top_k=settings.top_k,
            top_p=settings.top_p,
            repetition_penalty=settings.repetition_penalty,
            llm_provider=settings.llm_provider,
            rag_llm=settings.rag_llm,
        ),
        chunking=ChunkingSettings(
            chunking_strategy=settings.chunking_strategy,
            min_chunk_size=settings.min_chunk_size,
            max_chunk_size=settings.max_chunk_size,
            chunk_overlap=settings.chunk_overlap,
            semantic_threshold=settings.semantic_threshold,
        ),
        retrieval=RetrievalSettings(
            retrieval_type=settings.retrieval_type,
            number_of_results=settings.number_of_results,
            vector_weight=settings.vector_weight,
            keyword_weight=settings.keyword_weight,
            enable_reranking=settings.enable_reranking,
            reranker_type=settings.reranker_type,
            reranker_top_k=settings.reranker_top_k,
        ),
        embedding=EmbeddingSettings(
            embedding_model=settings.embedding_model,
            embedding_dim=settings.embedding_dim,
            embedding_batch_size=settings.embedding_batch_size,
            embedding_concurrency_limit=settings.embedding_concurrency_limit,
        ),
        cot=CoTSettings(
            cot_max_reasoning_depth=settings.cot_max_reasoning_depth,
            cot_reasoning_strategy=settings.cot_reasoning_strategy,
            cot_token_budget_multiplier=settings.cot_token_budget_multiplier,
        ),
        vector_db=settings.vector_db,
        log_level=settings.log_level,
    )
