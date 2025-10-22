"""Logging context management for async operation tracking.

This module provides context variables and utilities for tracking request context
across async operations in the RAG pipeline. It enables automatic context propagation
for structured logging without manual parameter passing.

Example:
    >>> from core.logging_context import log_operation, pipeline_stage_context
    >>> from core.logging_utils import get_logger
    >>>
    >>> logger = get_logger(__name__)
    >>>
    >>> async def search(collection_id: str, user_id: str):
    ...     with log_operation(logger, "search_documents", "collection", collection_id, user_id=user_id):
    ...         with pipeline_stage_context("query_rewriting"):
    ...             logger.info("Rewriting query")
    ...         with pipeline_stage_context("vector_search"):
    ...             logger.info("Searching vectors")
"""

import time
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from logging import Logger
from typing import Any


@dataclass
class LogContext:
    """Context information for structured logging.

    Attributes:
        request_id: Unique identifier for request tracing
        user_id: ID of the user making the request
        collection_id: ID of the collection being accessed
        pipeline_id: ID of the pipeline being used
        document_id: ID of the document being processed
        operation: Current operation name
        pipeline_stage: Current RAG pipeline stage
        metadata: Additional arbitrary metadata
    """

    request_id: str | None = None
    user_id: str | None = None
    collection_id: str | None = None
    pipeline_id: str | None = None
    document_id: str | None = None
    operation: str | None = None
    pipeline_stage: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert context to dictionary for logging.

        Returns:
            Dictionary representation of non-None context fields
        """
        return {
            k: v
            for k, v in {
                "request_id": self.request_id,
                "user_id": self.user_id,
                "collection_id": self.collection_id,
                "pipeline_id": self.pipeline_id,
                "document_id": self.document_id,
                "operation": self.operation,
                "pipeline_stage": self.pipeline_stage,
                **self.metadata,
            }.items()
            if v is not None
        }


# Context variable for async propagation
_log_context: ContextVar[LogContext | None] = ContextVar("log_context", default=None)


def get_context() -> LogContext:
    """Get the current log context.

    Returns:
        Current LogContext instance
    """
    context = _log_context.get()
    if context is None:
        context = LogContext()
        _log_context.set(context)
    return context


def set_context(context: LogContext) -> None:
    """Set the current log context.

    Args:
        context: LogContext to set as current
    """
    _log_context.set(context)


def clear_context() -> None:
    """Clear the current log context by resetting to default."""
    _log_context.set(LogContext())


def update_context(**kwargs: Any) -> None:
    """Update the current context with new values.

    Args:
        **kwargs: Context fields to update (request_id, user_id, etc.)
    """
    context = get_context()
    for key, value in kwargs.items():
        if hasattr(context, key):
            setattr(context, key, value)
        else:
            context.metadata[key] = value
    set_context(context)


@contextmanager
def log_operation(
    logger: Logger,
    operation: str,
    entity_type: str,
    entity_id: str,
    user_id: str | None = None,
    **metadata: Any,
) -> Generator[None, None, None]:
    """Context manager for tracking an operation with automatic timing.

    This context manager:
    1. Generates a request ID if not already set
    2. Sets the operation name and entity context
    3. Logs operation start
    4. Times the operation
    5. Logs operation completion with duration
    6. Restores previous context on exit

    Args:
        logger: Logger instance to use
        operation: Name of the operation (e.g., "search_documents")
        entity_type: Type of entity (e.g., "collection", "user", "pipeline")
        entity_id: ID of the entity
        user_id: Optional user ID for the request
        **metadata: Additional metadata to include in logs

    Example:
        >>> with log_operation(logger, "search", "collection", "abc123", user_id="user456"):
        ...     # Operation code here
        ...     pass
    """
    # Save previous context
    prev_context = get_context()

    # Create new context with operation details
    new_context = LogContext(
        request_id=prev_context.request_id or f"req_{uuid.uuid4().hex[:12]}",
        user_id=user_id or prev_context.user_id,
        operation=operation,
        metadata=metadata,
    )

    # Set entity-specific context
    if entity_type == "collection":
        new_context.collection_id = entity_id
    elif entity_type == "pipeline":
        new_context.pipeline_id = entity_id
    elif entity_type == "document":
        new_context.document_id = entity_id
    elif entity_type == "user":
        new_context.user_id = entity_id

    # Preserve other context from previous
    if prev_context.collection_id and not new_context.collection_id:
        new_context.collection_id = prev_context.collection_id
    if prev_context.pipeline_id and not new_context.pipeline_id:
        new_context.pipeline_id = prev_context.pipeline_id
    if prev_context.pipeline_stage:
        new_context.pipeline_stage = prev_context.pipeline_stage

    set_context(new_context)

    # Log operation start
    start_time = time.time()
    logger.info(
        f"Starting {operation}",
        extra={
            "context": new_context.to_dict(),
            "entity_type": entity_type,
            "entity_id": entity_id,
        },
    )

    try:
        yield
    except Exception as e:
        # Log operation failure with timing
        duration_ms = (time.time() - start_time) * 1000
        logger.error(
            f"Failed {operation}: {e!s}",
            extra={
                "context": new_context.to_dict(),
                "entity_type": entity_type,
                "entity_id": entity_id,
                "execution_time_ms": duration_ms,
                "error": str(e),
            },
            exc_info=True,
        )
        raise
    finally:
        # Log operation completion with timing
        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            f"Completed {operation}",
            extra={
                "context": new_context.to_dict(),
                "entity_type": entity_type,
                "entity_id": entity_id,
                "execution_time_ms": duration_ms,
            },
        )

        # Restore previous context
        set_context(prev_context)


@contextmanager
def pipeline_stage_context(stage: str) -> Generator[None, None, None]:
    """Context manager for tracking pipeline stage transitions.

    Args:
        stage: Pipeline stage name (e.g., "query_rewriting", "vector_search")

    Example:
        >>> with pipeline_stage_context("query_rewriting"):
        ...     # Query rewriting code
        ...     pass
    """
    # Save previous context
    prev_context = get_context()

    # Create new context with updated pipeline stage
    new_context = LogContext(
        request_id=prev_context.request_id,
        user_id=prev_context.user_id,
        collection_id=prev_context.collection_id,
        pipeline_id=prev_context.pipeline_id,
        document_id=prev_context.document_id,
        operation=prev_context.operation,
        pipeline_stage=stage,
        metadata=prev_context.metadata.copy(),
    )

    set_context(new_context)

    try:
        yield
    finally:
        # Restore previous context
        set_context(prev_context)


@contextmanager
def request_context(
    request_id: str | None = None,
    user_id: str | None = None,
    **metadata: Any,
) -> Generator[None, None, None]:
    """Context manager for setting request-level context.

    Args:
        request_id: Request correlation ID (auto-generated if not provided)
        user_id: User making the request
        **metadata: Additional request metadata

    Example:
        >>> with request_context(user_id="user123", collection_id="coll456"):
        ...     # Request handling code
        ...     pass
    """
    # Save previous context
    prev_context = get_context()

    # Create new context
    new_context = LogContext(
        request_id=request_id or f"req_{uuid.uuid4().hex[:12]}",
        user_id=user_id,
        metadata=metadata,
    )

    set_context(new_context)

    try:
        yield
    finally:
        # Restore previous context
        set_context(prev_context)


def get_log_extra() -> dict[str, Any]:
    """Get current context as extra dict for logging.

    Returns:
        Dictionary suitable for logger.info(..., extra=get_log_extra())
    """
    context = get_context()
    return {"context": context.to_dict()}


# Common pipeline stages for RAG operations
class PipelineStage:
    """Standard pipeline stage names for consistency."""

    # Query processing stages
    QUERY_VALIDATION = "query_validation"
    QUERY_REWRITING = "query_rewriting"
    QUERY_EXPANSION = "query_expansion"
    QUERY_DECOMPOSITION = "query_decomposition"

    # Embedding stages
    EMBEDDING_GENERATION = "embedding_generation"
    EMBEDDING_BATCHING = "embedding_batching"

    # Retrieval stages
    VECTOR_SEARCH = "vector_search"
    KEYWORD_SEARCH = "keyword_search"
    HYBRID_SEARCH = "hybrid_search"
    DOCUMENT_RETRIEVAL = "document_retrieval"
    METADATA_GENERATION = "metadata_generation"

    # Reranking stages
    RERANKING = "reranking"
    RELEVANCE_SCORING = "relevance_scoring"

    # Generation stages
    PROMPT_CONSTRUCTION = "prompt_construction"
    LLM_GENERATION = "llm_generation"
    ANSWER_PROCESSING = "answer_processing"
    SOURCE_ATTRIBUTION = "source_attribution"

    # Chain of Thought stages
    COT_REASONING = "cot_reasoning"
    COT_QUESTION_DECOMPOSITION = "cot_question_decomposition"
    COT_ANSWER_SYNTHESIS = "cot_answer_synthesis"

    # Document processing stages
    DOCUMENT_PROCESSING = "document_processing"
    DOCUMENT_PARSING = "document_parsing"
    DOCUMENT_CHUNKING = "document_chunking"
    DOCUMENT_INDEXING = "document_indexing"

    # Collection management stages
    COLLECTION_CREATION = "collection_creation"
    COLLECTION_VALIDATION = "collection_validation"
    COLLECTION_DELETION = "collection_deletion"
