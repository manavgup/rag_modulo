"""Core abstractions for the RAG technique system.

This module defines the base classes and types used throughout the technique framework:
- BaseTechnique: Abstract base class all techniques must implement
- TechniqueStage: Enum defining pipeline stages
- TechniqueContext: Shared context passed through the pipeline
- TechniqueResult: Standardized result format
- TechniqueMetadata: Technique metadata and characteristics
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar, TypeVar

from pydantic import UUID4, BaseModel

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from rag_solution.generation.providers.base import LLMBase
    from vectordbs.data_types import QueryResult

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


class TechniqueStage(str, Enum):
    """Pipeline stages where techniques can be applied.

    Techniques are organized into stages that execute in sequence:
    1. QUERY_PREPROCESSING - Initial query cleaning and validation
    2. QUERY_TRANSFORMATION - Query enhancement (rewriting, expansion, etc.)
    3. RETRIEVAL - Document retrieval from vector store
    4. POST_RETRIEVAL - Post-retrieval processing (filtering, deduplication)
    5. RERANKING - Result reordering based on relevance
    6. COMPRESSION - Context compression to reduce token usage
    7. GENERATION - Answer generation from retrieved context
    """

    QUERY_PREPROCESSING = "query_preprocessing"
    QUERY_TRANSFORMATION = "query_transformation"
    RETRIEVAL = "retrieval"
    POST_RETRIEVAL = "post_retrieval"
    RERANKING = "reranking"
    COMPRESSION = "compression"
    GENERATION = "generation"


@dataclass
class TechniqueMetadata:
    """Metadata describing a technique's characteristics.

    This metadata is used for:
    - Displaying available techniques to users
    - Validating technique compatibility
    - Estimating execution cost and latency
    - Determining resource requirements
    """

    technique_id: str
    name: str
    description: str
    stage: TechniqueStage

    # Resource requirements
    requires_llm: bool = False
    requires_embeddings: bool = False
    requires_vector_store: bool = False

    # Performance characteristics
    estimated_latency_ms: int = 0
    token_cost_multiplier: float = 1.0

    # Compatibility
    compatible_with: list[str] = field(default_factory=list)
    incompatible_with: list[str] = field(default_factory=list)

    # Configuration
    default_config: dict[str, Any] = field(default_factory=dict)
    config_schema: dict[str, Any] | None = None


@dataclass
class TechniqueContext:
    """Context shared across technique pipeline.

    This context object is passed through the entire pipeline, allowing techniques
    to share data and coordinate their execution. It contains:
    - Request information (user, collection, query)
    - Service dependencies (LLM provider, vector store, DB session)
    - Pipeline state (current query, retrieved documents)
    - Metrics and tracing data

    Techniques can:
    - Read from the context to get input data
    - Write to intermediate_results to share data with later techniques
    - Update current_query to transform the query
    - Add to retrieved_documents to provide retrieval results
    """

    # Request context
    user_id: UUID4
    collection_id: UUID4
    original_query: str

    # Services (dependency injection)
    llm_provider: LLMBase | None = None
    vector_store: Any | None = None
    db_session: Session | None = None

    # Pipeline state (mutable)
    current_query: str = ""
    retrieved_documents: list[QueryResult] = field(default_factory=list)
    intermediate_results: dict[str, Any] = field(default_factory=dict)

    # Metrics and observability
    metrics: dict[str, Any] = field(default_factory=dict)
    execution_trace: list[str] = field(default_factory=list)

    # Configuration
    config: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Initialize current_query to original_query if not set."""
        if not self.current_query:
            self.current_query = self.original_query


@dataclass
class TechniqueResult(Generic[OutputT]):
    """Standardized result from technique execution.

    All techniques return this standardized result format, which includes:
    - success: Whether the technique executed successfully
    - output: The technique's output data (type varies by technique)
    - metadata: Additional information about the execution
    - metrics: Performance and cost metrics
    - error: Error message if execution failed
    - fallback_used: Whether a fallback strategy was used

    This standardization enables:
    - Consistent error handling across techniques
    - Uniform metrics collection
    - Pipeline resilience (continue on failure)
    - Observability and debugging
    """

    success: bool
    output: OutputT
    metadata: dict[str, Any]
    technique_id: str
    execution_time_ms: float

    # Metrics
    tokens_used: int = 0
    llm_calls: int = 0

    # Observability
    trace_info: dict[str, Any] = field(default_factory=dict)

    # Error handling
    error: str | None = None
    fallback_used: bool = False


class BaseTechnique(ABC, Generic[InputT, OutputT]):
    """Abstract base class for all RAG techniques.

    All techniques must:
    1. Define metadata (ID, name, description, stage, requirements)
    2. Implement execute() to perform the technique logic
    3. Implement validate_config() to validate configuration
    4. Optionally implement get_default_config() for defaults

    Techniques should be:
    - Stateless (all state in TechniqueContext)
    - Resilient (handle errors gracefully, provide fallbacks)
    - Observable (log execution, record metrics)
    - Configurable (validate and use config from context)

    Example:
        class MyTechnique(BaseTechnique[str, str]):
            technique_id = "my_technique"
            name = "My Technique"
            description = "Does something useful"
            stage = TechniqueStage.QUERY_TRANSFORMATION

            async def execute(self, context: TechniqueContext) -> TechniqueResult[str]:
                # Implementation here
                return TechniqueResult(
                    success=True,
                    output=transformed_query,
                    metadata={},
                    technique_id=self.technique_id,
                    execution_time_ms=0
                )

            def validate_config(self, config: dict[str, Any]) -> bool:
                return True  # Validation logic
    """

    # Metadata - must be defined by subclasses
    technique_id: str
    name: str
    description: str
    stage: TechniqueStage

    # Resource requirements
    requires_llm: bool = False
    requires_embeddings: bool = False
    requires_vector_store: bool = False

    # Performance characteristics
    estimated_latency_ms: int = 0
    token_cost_multiplier: float = 1.0

    # Compatibility
    compatible_with: ClassVar[list[str]] = []
    incompatible_with: ClassVar[list[str]] = []

    @abstractmethod
    async def execute(self, context: TechniqueContext) -> TechniqueResult[OutputT]:
        """Execute the technique.

        Args:
            context: Shared pipeline context containing all necessary data and services

        Returns:
            TechniqueResult containing the output and execution metadata

        Raises:
            Should not raise exceptions - return TechniqueResult with success=False instead
        """

    @abstractmethod
    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate technique-specific configuration.

        Args:
            config: Configuration dictionary to validate

        Returns:
            True if configuration is valid, False otherwise

        Note:
            Should not raise exceptions - return False for invalid config
        """

    def get_metadata(self) -> TechniqueMetadata:
        """Return technique metadata.

        Returns:
            TechniqueMetadata object describing this technique
        """
        return TechniqueMetadata(
            technique_id=self.technique_id,
            name=self.name,
            description=self.description,
            stage=self.stage,
            requires_llm=self.requires_llm,
            requires_embeddings=self.requires_embeddings,
            requires_vector_store=self.requires_vector_store,
            estimated_latency_ms=self.estimated_latency_ms,
            token_cost_multiplier=self.token_cost_multiplier,
            compatible_with=self.compatible_with,
            incompatible_with=self.incompatible_with,
            default_config=self.get_default_config(),
            config_schema=self.get_config_schema(),
        )

    def get_default_config(self) -> dict[str, Any]:
        """Get default configuration for this technique.

        Returns:
            Dictionary of default configuration values

        Note:
            Override in subclasses to provide technique-specific defaults
        """
        return {}

    def get_config_schema(self) -> dict[str, Any] | None:
        """Get JSON schema for configuration validation.

        Returns:
            JSON schema dictionary or None if no schema defined

        Note:
            Override in subclasses to provide configuration schema for validation
        """
        return None

    async def execute_with_timing(self, context: TechniqueContext) -> TechniqueResult[OutputT]:
        """Execute technique with automatic timing.

        This wrapper method handles:
        - Execution timing
        - Error handling
        - Metrics collection
        - Tracing

        Args:
            context: Pipeline context

        Returns:
            TechniqueResult with timing and error handling
        """
        start_time = time.time()

        try:
            result = await self.execute(context)
            execution_time = (time.time() - start_time) * 1000
            result.execution_time_ms = execution_time
            return result

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return TechniqueResult(
                success=False,
                output=None,  # type: ignore[arg-type]
                metadata={"error_type": type(e).__name__},
                technique_id=self.technique_id,
                execution_time_ms=execution_time,
                error=str(e),
            )


class TechniqueConfig(BaseModel):
    """Configuration for a single technique in the pipeline.

    This model is used in API requests to configure which techniques to apply
    and how they should be configured.

    Attributes:
        technique_id: Unique identifier for the technique
        enabled: Whether to execute this technique (allows conditional execution)
        config: Technique-specific configuration parameters
        fallback_enabled: Whether to use fallback on failure (default: True)
    """

    technique_id: str
    enabled: bool = True
    config: dict[str, Any] = {}
    fallback_enabled: bool = True

    class Config:
        """Pydantic config."""

        extra = "forbid"  # Reject unknown fields
