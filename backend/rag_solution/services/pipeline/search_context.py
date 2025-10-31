"""
Search context for inter-stage data flow.

This module defines the SearchContext dataclass that carries data between
pipeline stages, accumulating results as the search progresses.
"""

import time
from dataclasses import dataclass, field
from typing import Any

from pydantic import UUID4

from rag_solution.schemas.chain_of_thought_schema import ChainOfThoughtOutput
from rag_solution.schemas.llm_usage_schema import TokenWarning
from rag_solution.schemas.search_schema import SearchInput
from vectordbs.data_types import DocumentMetadata, QueryResult


@dataclass
class SearchContext:  # pylint: disable=too-many-instance-attributes
    # Justification: Context object needs many attributes to track full search state
    """
    Context object that flows through the search pipeline.

    This object accumulates results from each stage and serves as the
    single source of truth for the search operation's state.

    Attributes:
        # Input
        search_input: Original search request
        user_id: User making the request
        collection_id: Collection being searched

        # Pipeline Configuration
        pipeline_id: Resolved pipeline ID
        collection_name: Vector DB collection name

        # Retrieval Results
        query_results: Retrieved documents
        rewritten_query: Query after enhancement
        document_metadata: Metadata about retrieved documents

        # Generation Results
        generated_answer: Final answer from LLM
        evaluation: Answer quality evaluation
        cot_output: Chain of Thought reasoning steps
        token_warning: Token usage warnings

        # Execution Metadata
        start_time: When search started
        execution_time: Total search execution time
        metadata: Additional metadata from stages
        errors: Accumulated non-fatal errors
    """

    # Input
    search_input: SearchInput
    user_id: UUID4
    collection_id: UUID4

    # Pipeline Configuration
    pipeline_id: UUID4 | None = None
    collection_name: str | None = None

    # Retrieval Results
    query_results: list[QueryResult] = field(default_factory=list)
    rewritten_query: str | None = None
    document_metadata: list[DocumentMetadata] = field(default_factory=list)

    # Generation Results
    generated_answer: str = ""
    evaluation: dict[str, Any] | None = None
    cot_output: ChainOfThoughtOutput | None = None
    token_warning: TokenWarning | None = None

    # Execution Metadata
    start_time: float = field(default_factory=time.time)
    execution_time: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def update_execution_time(self) -> None:
        """Update execution time based on start time."""
        self.execution_time = time.time() - self.start_time

    def add_error(self, error: str) -> None:
        """
        Add a non-fatal error to the context.

        Args:
            error: Error message
        """
        self.errors.append(error)

    def add_metadata(self, key: str, value: Any) -> None:
        """
        Add metadata to the context.

        Args:
            key: Metadata key
            value: Metadata value
        """
        self.metadata[key] = value
