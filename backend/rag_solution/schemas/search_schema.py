"""API schemas for search functionality."""

from typing import Any

from pydantic import UUID4, BaseModel, ConfigDict, Field

from rag_solution.schemas.llm_usage_schema import TokenWarning
from rag_solution.techniques.base import TechniqueConfig
from vectordbs.data_types import DocumentMetadata, QueryResult


class SearchInput(BaseModel):
    """Input schema for search requests.

    Defines the structure of search requests to the API.
    Supports dynamic technique selection for runtime RAG customization.

    Attributes:
        question: The user's query text
        collection_id: UUID4 of the collection to search in
        user_id: UUID4 of the requesting user
        techniques: Optional list of techniques to apply (dynamic selection)
        technique_preset: Optional preset name ("default", "fast", "accurate", "cost_optimized")
        config_metadata: Optional search configuration parameters (legacy, maintained for backward compatibility)

    Examples:
        # Using techniques directly
        SearchInput(
            question="What is ML?",
            collection_id=uuid,
            user_id=uuid,
            techniques=[
                TechniqueConfig(technique_id="hyde"),
                TechniqueConfig(technique_id="vector_retrieval", config={"top_k": 10}),
                TechniqueConfig(technique_id="reranking", config={"top_k": 5})
            ]
        )

        # Using a preset
        SearchInput(
            question="What is ML?",
            collection_id=uuid,
            user_id=uuid,
            technique_preset="accurate"
        )

        # Legacy format (still supported)
        SearchInput(
            question="What is ML?",
            collection_id=uuid,
            user_id=uuid,
            config_metadata={"top_k": 10}
        )
    """

    question: str
    collection_id: UUID4
    user_id: UUID4

    # New technique system (optional)
    techniques: list[TechniqueConfig] | None = Field(
        default=None,
        description="List of techniques to apply in the RAG pipeline. "
        "If not specified, uses technique_preset or defaults to 'default' preset.",
    )

    technique_preset: str | None = Field(
        default=None,
        description="Preset technique configuration: 'default', 'fast', 'accurate', 'cost_optimized', 'comprehensive'. "
        "Ignored if 'techniques' is specified.",
    )

    # Legacy configuration (backward compatible)
    config_metadata: dict[str, Any] | None = Field(
        default=None,
        description="Legacy configuration metadata. Maintained for backward compatibility. "
        "Prefer using 'techniques' or 'technique_preset' for new implementations.",
    )

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class SearchOutput(BaseModel):
    """Output schema for search responses.

    Defines the structure of search responses from the API.
    This maps directly to what the UI needs to display:
    - The generated answer
    - List of document metadata for showing document info
    - List of chunks with their scores for showing relevant passages
    - Technique execution information for observability

    Attributes:
        answer: Generated answer to the query
        documents: List of document metadata for UI display
        query_results: List of QueryResult
        rewritten_query: Optional rewritten version of the original query
        evaluation: Optional evaluation metrics and results
        execution_time: Total execution time in milliseconds
        cot_output: Chain of Thought reasoning steps when requested
        metadata: Additional metadata including conversation context and technique execution
        token_warning: Token usage warning if approaching limits
        techniques_applied: List of technique IDs that were applied (for observability)
        technique_metrics: Metrics for each technique execution (for debugging)
    """

    answer: str
    documents: list[DocumentMetadata]
    query_results: list[QueryResult]
    rewritten_query: str | None = None
    evaluation: dict[str, Any] | None = None
    execution_time: float | None = None
    cot_output: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    token_warning: TokenWarning | None = None

    # New technique system observability
    techniques_applied: list[str] | None = Field(
        default=None, description="List of technique IDs applied in this search (execution order)"
    )
    technique_metrics: dict[str, Any] | None = Field(
        default=None,
        description="Performance metrics for each technique (execution time, tokens, success)",
    )

    model_config = ConfigDict(from_attributes=True)
