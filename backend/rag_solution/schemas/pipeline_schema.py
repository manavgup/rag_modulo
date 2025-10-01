"""Schema definitions for pipeline configuration."""

# Type alias for the database model to avoid circular imports
from contextlib import suppress
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import UUID4, BaseModel, ConfigDict, Field, field_validator, model_validator
from vectordbs.data_types import QueryResult

from rag_solution.models.pipeline import PipelineConfig as PipelineModel


class ChunkingStrategy(str, Enum):
    """Available chunking strategies."""

    FIXED = "fixed"
    SEMANTIC = "semantic"
    OVERLAP = "overlap"
    PARAGRAPH = "paragraph"


class RetrieverType(str, Enum):
    """Available retriever types."""

    VECTOR = "vector"
    KEYWORD = "keyword"
    HYBRID = "hybrid"


class ContextStrategy(str, Enum):
    """Available context handling strategies."""

    SIMPLE = "simple"
    PRIORITY = "priority"
    WEIGHTED = "weighted"


class PipelineConfigBase(BaseModel):
    """Base schema for Pipeline Configuration with enhanced validation."""

    name: str = Field(..., min_length=1, max_length=255, description="Name of the pipeline configuration")
    description: str | None = Field(None, max_length=1024, description="Description of the pipeline configuration")
    chunking_strategy: ChunkingStrategy = Field(
        default=ChunkingStrategy.FIXED, description="Strategy for chunking text data"
    )
    embedding_model: str = Field(..., min_length=1, description="Embedding model to use for text data")
    retriever: RetrieverType = Field(default=RetrieverType.VECTOR, description="Retriever type for document search")
    context_strategy: ContextStrategy = Field(
        default=ContextStrategy.PRIORITY, description="Strategy for handling context chunks"
    )
    enable_logging: bool = Field(default=True, description="Enable or disable pipeline logging")
    max_context_length: int | None = Field(
        default=2048, ge=128, le=8192, description="Maximum context length in tokens"
    )
    timeout: float | None = Field(default=30.0, ge=1.0, le=300.0, description="Timeout in seconds for pipeline tasks")
    config_metadata: dict[str, Any] | None = Field(default=None, description="Additional metadata for the pipeline")
    is_default: bool = Field(default=False, description="Whether this is the default pipeline")

    model_config = ConfigDict(
        validate_assignment=True,
        validate_default=True,
        extra="forbid",
        frozen=False,
        str_strip_whitespace=True,
        use_enum_values=True,
        json_encoders={UUID4: str},
    )

    @field_validator("embedding_model")
    @classmethod
    def validate_embedding_model(cls, v: str) -> str:
        """Validate embedding model name format."""
        if not any(prefix in v for prefix in ["sentence-transformers/", "openai/", "google/", "microsoft/"]):
            raise ValueError("Invalid embedding model format")
        return v

    @model_validator(mode="after")
    def validate_hybrid_retriever_config(self) -> "PipelineConfigBase":
        """Validate hybrid retriever configuration."""
        if self.retriever == RetrieverType.HYBRID and not self.config_metadata:
            raise ValueError("Hybrid retriever requires configuration in metadata")
        return self


class PipelineConfigInput(PipelineConfigBase):
    """Input schema for pipeline configuration."""

    user_id: UUID4 = Field(..., description="ID of the owner user")
    collection_id: UUID4 | None = Field(None, description="ID of the associated collection")
    provider_id: UUID4 = Field(..., description="ID of the LLM provider to use")

    @model_validator(mode="before")
    @classmethod
    def convert_str_to_uuid(cls, data: Any) -> Any:
        """Convert string UUIDs to UUID objects."""
        if isinstance(data, dict):
            for field in ["user_id", "provider_id", "collection_id"]:
                if field in data and isinstance(data[field], str):
                    with suppress(ValueError, AttributeError):
                        data[field] = UUID4(data[field])
        return data


class LLMProviderInfo(BaseModel):
    """Schema for LLM provider information."""

    id: UUID4
    name: str
    base_url: str | None = None
    is_active: bool = True
    is_default: bool = False


class PipelineConfigOutput(PipelineConfigBase):
    """Output schema for pipeline configuration with timestamps."""

    id: UUID4 = Field(..., description="Unique identifier for the configuration")
    user_id: UUID4
    collection_id: UUID4 | None
    provider_id: UUID4
    provider: LLMProviderInfo | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_db_model(cls, model: PipelineModel) -> "PipelineConfigOutput":
        """
        Convert database model to output schema.

        Args:
            model: Database model instance of type PipelineConfig

        Returns:
            PipelineConfigOutput instance

        Raises:
            ValueError: If conversion fails
        """
        try:
            provider_info = None
            if model.provider:
                # The provider relationship should be loaded with lazy="selectin"
                provider_info = LLMProviderInfo(
                    id=model.provider.id,
                    name=model.provider.name,
                    base_url=model.provider.base_url,
                    is_active=model.provider.is_active,
                    is_default=model.provider.is_default,
                )

            return cls.model_validate(
                {
                    "id": model.id,
                    "name": model.name,
                    "description": model.description,
                    "chunking_strategy": model.chunking_strategy,
                    "embedding_model": model.embedding_model,
                    "retriever": model.retriever,
                    "context_strategy": model.context_strategy,
                    "provider_id": model.provider_id,
                    "provider": provider_info,
                    "collection_id": model.collection_id,
                    "user_id": model.user_id,
                    "enable_logging": model.enable_logging,
                    "max_context_length": model.max_context_length,
                    "timeout": model.timeout,
                    "config_metadata": model.config_metadata,
                    "created_at": model.created_at,
                    "updated_at": model.updated_at,
                    "is_default": model.is_default,
                }
            )
        except Exception as e:
            raise ValueError(f"Failed to convert database model: {e!s}") from e


class PipelineResult(BaseModel):
    """Result from pipeline operations with enhanced validation."""

    success: bool = Field(..., description="Operation success status")
    error: str | None = Field(None, description="Error message if operation failed")
    warnings: list[str] | None = Field(default=None, description="Warning messages")
    rewritten_query: str | None = Field(None, min_length=1)
    query_results: list[QueryResult] | None = None
    generated_answer: str | None = Field(None)
    evaluation: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True, validate_assignment=True, arbitrary_types_allowed=True)

    @field_validator("query_results")
    @classmethod
    def validate_query_results(cls, v: list[QueryResult] | None) -> list[QueryResult] | None:
        """Validate query results are properly formatted."""
        if v is not None:
            for result in v:
                if not result.chunk or not result.chunk.text:
                    raise ValueError("Invalid query result format")
        return v

    def get_sorted_results(self) -> list[QueryResult]:
        """Get results sorted by similarity score."""
        return sorted(self.query_results or [], key=lambda x: x.score, reverse=True)

    def get_top_k_results(self, k: int) -> list[QueryResult]:
        """Get top k results by similarity score."""
        return self.get_sorted_results()[:k]

    def get_all_texts(self) -> list[str]:
        """Get all chunk texts from results."""
        return [result.chunk.text for result in (self.query_results or [])]

    def get_unique_document_ids(self) -> set[str]:
        """Get set of unique document IDs from results."""
        return {result.document_id for result in (self.query_results or []) if result.document_id is not None}

    def get_results_for_document(self, document_id: str) -> list[QueryResult]:
        """Get all results from a specific document."""
        return [result for result in (self.query_results or []) if result.document_id == document_id]
