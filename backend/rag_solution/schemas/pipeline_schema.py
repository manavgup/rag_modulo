"""Schema definitions for pipeline configuration."""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List, TypeAlias
from pydantic import (
    BaseModel,
    Field,
    UUID4,
    ConfigDict,
    field_validator,
    model_validator
)
from vectordbs.data_types import QueryResult

# Type alias for the database model to avoid circular imports
PipelineModel: TypeAlias = "PipelineConfig"

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
    
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Name of the pipeline configuration"
    )
    description: Optional[str] = Field(
        None,
        max_length=1024,
        description="Description of the pipeline configuration"
    )
    chunking_strategy: ChunkingStrategy = Field(
        default=ChunkingStrategy.FIXED,
        description="Strategy for chunking text data"
    )
    embedding_model: str = Field(
        ...,
        min_length=1,
        description="Embedding model to use for text data"
    )
    retriever: RetrieverType = Field(
        default=RetrieverType.VECTOR,
        description="Retriever type for document search"
    )
    context_strategy: ContextStrategy = Field(
        default=ContextStrategy.PRIORITY,
        description="Strategy for handling context chunks"
    )
    enable_logging: bool = Field(
        default=True,
        description="Enable or disable pipeline logging"
    )
    max_context_length: Optional[int] = Field(
        default=2048,
        ge=128,
        le=8192,
        description="Maximum context length in tokens"
    )
    timeout: Optional[float] = Field(
        default=30.0,
        ge=1.0,
        le=300.0,
        description="Timeout in seconds for pipeline tasks"
    )
    config_metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional metadata for the pipeline"
    )
    is_default: bool = Field(
        default=False,
        description="Whether this is the default pipeline"
    )

    model_config = ConfigDict(
        validate_assignment=True,
        validate_default=True,
        extra="forbid",
        frozen=False,
        str_strip_whitespace=True,
        use_enum_values=True
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
    
    @model_validator(mode="after")
    def validate_default_settings(self) -> "PipelineConfigBase":
        """Validate default pipeline settings."""
        if self.is_default and self.collection_id is None:
            raise ValueError("Default pipeline must be associated with a collection")
        return self

class PipelineConfigInput(PipelineConfigBase):
    """Input schema for pipeline configuration."""
    collection_id: Optional[UUID4] = Field(
        None,
        description="ID of the associated collection"
    )
    provider_id: UUID4 = Field(
        ...,
        description="ID of the LLM provider to use"
    )

class PipelineConfigOutput(PipelineConfigBase):
    """Output schema for pipeline configuration with timestamps."""
    id: UUID4 = Field(..., description="Unique identifier for the configuration")
    collection_id: Optional[UUID4]
    provider_id: UUID4
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
            return cls.model_validate({
                "id": model.id,
                "name": model.name,
                "description": model.description,
                "chunking_strategy": model.chunking_strategy,
                "embedding_model": model.embedding_model,
                "retriever": model.retriever,
                "context_strategy": model.context_strategy,
                "provider_id": model.provider_id,
                "collection_id": model.collection_id,
                "enable_logging": model.enable_logging,
                "max_context_length": model.max_context_length,
                "timeout": model.timeout,
                "config_metadata": model.config_metadata,
                "created_at": model.created_at,
                "updated_at": model.updated_at,
                "is_default": model.is_default
            })
        except Exception as e:
            raise ValueError(f"Failed to convert database model: {str(e)}")

class PipelineResult(BaseModel):
    """Result from pipeline operations with enhanced validation."""
    success: bool = Field(..., description="Operation success status")
    error: Optional[str] = Field(None, description="Error message if operation failed")
    warnings: Optional[List[str]] = Field(default=None, description="Warning messages")
    rewritten_query: Optional[str] = Field(None, min_length=1)
    query_results: Optional[List[QueryResult]] = None
    generated_answer: Optional[str] = Field(None, min_length=1)
    evaluation: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        arbitrary_types_allowed=True
    )

    @field_validator("query_results")
    @classmethod
    def validate_query_results(cls, v: Optional[List[QueryResult]]) -> Optional[List[QueryResult]]:
        """Validate query results are properly formatted."""
        if v is not None:
            for result in v:
                if not result.chunk or not result.chunk.text:
                    raise ValueError("Invalid query result format")
        return v

    def get_sorted_results(self) -> List[QueryResult]:
        """Get results sorted by similarity score."""
        return sorted(self.query_results or [], key=lambda x: x.score, reverse=True)

    def get_top_k_results(self, k: int) -> List[QueryResult]:
        """Get top k results by similarity score."""
        return self.get_sorted_results()[:k]

    def get_all_texts(self) -> List[str]:
        """Get all chunk texts from results."""
        return [result.chunk.text for result in (self.query_results or [])]

    def get_unique_document_ids(self) -> set[str]:
        """Get set of unique document IDs from results."""
        return {
            result.document_id
            for result in (self.query_results or [])
            if result.document_id is not None
        }

    def get_results_for_document(self, document_id: str) -> List[QueryResult]:
        """Get all results from a specific document."""
        return [
            result for result in (self.query_results or [])
            if result.document_id == document_id
        ]