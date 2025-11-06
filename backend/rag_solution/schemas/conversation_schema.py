"""Conversation schemas for Chat with Documents feature.

This module defines Pydantic schemas for conversation sessions, messages,
context management, and question suggestions.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import UUID4, BaseModel, ConfigDict, Field, field_validator

from core.logging_utils import get_logger

logger = get_logger("conversation.schema")


class SessionStatus(str, Enum):
    """Status of a conversation session."""

    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"
    EXPIRED = "expired"
    DELETED = "deleted"


class MessageRole(str, Enum):
    """Role of a message sender."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageType(str, Enum):
    """Type of message content."""

    QUESTION = "question"
    ANSWER = "answer"
    FOLLOW_UP = "follow_up"
    CLARIFICATION = "clarification"
    ERROR = "error"
    SYSTEM = "system"
    SYSTEM_MESSAGE = "system_message"


class MessageMetadata(BaseModel):
    """Strongly typed metadata for conversation messages."""

    source_documents: list[str] | None = Field(
        default=None, description="Names/filenames of source documents used in the response"
    )
    search_metadata: dict[str, Any] | None = Field(default=None, description="Search result metadata")
    cot_used: bool = Field(default=False, description="Whether Chain of Thought was used")
    conversation_aware: bool = Field(default=False, description="Whether conversation context was used")
    execution_time: float | None = Field(default=None, description="Message processing time in seconds")
    token_count: int | None = Field(default=None, description="Number of tokens used")
    model_used: str | None = Field(default=None, description="LLM model used for generation")
    confidence_score: float | None = Field(default=None, description="Confidence score of the response")
    context_length: int | None = Field(default=None, description="Length of context used")
    token_analysis: dict[str, Any] | None = Field(default=None, description="Detailed token usage breakdown")

    model_config = ConfigDict(extra="allow")  # Allow additional fields for flexibility


class ExportFormat(str, Enum):
    """Format for exporting conversation data."""

    JSON = "json"
    CSV = "csv"
    TXT = "txt"
    PDF = "pdf"


class ConversationSessionCreateInput(BaseModel):
    """Input schema for creating a conversation session (without user_id)."""

    collection_id: UUID4 = Field(..., description="ID of the collection to chat with")
    session_name: str = Field(..., min_length=1, max_length=255, description="Name of the session")
    context_window_size: int = Field(default=4000, ge=1000, le=8000, description="Size of context window")
    max_messages: int = Field(default=50, ge=10, le=200, description="Maximum number of messages")
    is_archived: bool = Field(default=False, description="Whether the session is archived")
    is_pinned: bool = Field(default=False, description="Whether the session is pinned")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    model_config = {"validate_assignment": True, "str_strip_whitespace": True, "extra": "forbid"}

    @field_validator("context_window_size", mode="before")
    @classmethod
    def validate_context_window(cls, v: Any) -> int:
        """Validate context window size."""
        if isinstance(v, str):
            try:
                return int(v)
            except ValueError as e:
                msg = "Context window size must be a valid integer"
                raise ValueError(msg) from e
        return v


class ConversationSessionInput(BaseModel):
    """Input schema for creating a conversation session."""

    user_id: UUID4 = Field(..., description="ID of the user creating the session")
    collection_id: UUID4 = Field(..., description="ID of the collection to chat with")
    session_name: str = Field(..., min_length=1, max_length=255, description="Name of the session")
    context_window_size: int = Field(default=4000, ge=1000, le=8000, description="Size of context window")
    max_messages: int = Field(default=50, ge=10, le=200, description="Maximum number of messages")
    is_archived: bool = Field(default=False, description="Whether the session is archived")
    is_pinned: bool = Field(default=False, description="Whether the session is pinned")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    model_config = {"validate_assignment": True, "str_strip_whitespace": True, "extra": "forbid"}

    @field_validator("context_window_size", mode="before")
    @classmethod
    def round_context_window_size(cls, v: Any) -> int:
        """Round context window size to integer."""
        if isinstance(v, float):
            return int(v)  # Truncate instead of round
        return v

    def to_output(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        session_id: UUID4,
        status: SessionStatus = SessionStatus.ACTIVE,
        message_count: int = 0,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> "ConversationSessionOutput":
        """Convert input to output schema using Pydantic 2+ model validation."""
        if created_at is None:
            created_at = datetime.now(UTC)
        if updated_at is None:
            updated_at = datetime.now(UTC)

        # Use model_dump() to get all input data, then update with additional fields
        data = self.model_dump()
        data.update(
            {
                "id": session_id,
                "status": status,
                "message_count": message_count,
                "created_at": created_at,
                "updated_at": updated_at,
            }
        )

        return ConversationSessionOutput.model_validate(data)


class ConversationSessionOutput(BaseModel):
    """Output schema for conversation session."""

    id: UUID4 = Field(default_factory=uuid4, description="Unique session ID")
    user_id: UUID4 = Field(..., description="ID of the user")
    collection_id: UUID4 = Field(..., description="ID of the collection")
    session_name: str = Field(..., description="Name of the session")
    status: SessionStatus = Field(default=SessionStatus.ACTIVE, description="Status of the session")
    context_window_size: int = Field(..., description="Size of context window")
    max_messages: int = Field(..., description="Maximum number of messages")
    is_archived: bool = Field(default=False, description="Whether the session is archived")
    is_pinned: bool = Field(default=False, description="Whether the session is pinned")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Creation timestamp")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Last update timestamp")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    message_count: int = Field(default=0, description="Number of messages in the session")

    @classmethod
    def model_validate(cls, obj: Any, **kwargs) -> "ConversationSessionOutput":
        """Override model_validate to handle ConversationSession database models."""

        # Check if the input is a ConversationSession database model
        if hasattr(obj, "__tablename__") and getattr(obj, "__tablename__", None) == "conversation_sessions":
            return cls.from_db_session(
                obj, message_count=len(obj.messages) if hasattr(obj, "messages") and obj.messages else 0
            )

        # Otherwise use default model validation
        return super().model_validate(obj, **kwargs)

    @classmethod
    def from_db_session(cls, session: Any, message_count: int = 0) -> "ConversationSessionOutput":
        """Create ConversationSessionOutput from database session model."""
        try:
            # Debug logging

            # Ensure status is properly converted
            status_value = session.status
            if isinstance(status_value, str):
                # Convert string to SessionStatus enum
                status_value = SessionStatus(status_value)

            return cls(
                id=session.id,
                user_id=session.user_id,
                collection_id=session.collection_id,
                session_name=session.session_name,
                status=status_value,
                context_window_size=session.context_window_size,
                max_messages=session.max_messages,
                is_archived=session.is_archived,
                is_pinned=session.is_pinned,
                created_at=session.created_at,
                updated_at=session.updated_at,
                metadata=session.session_metadata or {},
                message_count=message_count,
            )
        except (ValueError, KeyError, AttributeError) as e:
            logger.error("Failed to create ConversationSessionOutput from database session: %s", str(e))
            raise


class ConversationMessageInput(BaseModel):
    """Input schema for conversation messages."""

    session_id: UUID4 = Field(..., description="ID of the session")
    content: str = Field(..., min_length=1, max_length=100000, description="Message content")
    role: MessageRole = Field(..., description="Role of the message sender")
    message_type: MessageType = Field(..., description="Type of message")
    metadata: MessageMetadata | dict[str, Any] | None = Field(default=None, description="Message metadata")
    token_count: int | None = Field(default=None, description="Token count for this message")
    execution_time: float | None = Field(default=None, description="Execution time in seconds")

    model_config = {"str_strip_whitespace": True}

    def to_output(self, message_id: UUID4, created_at: datetime | None = None) -> "ConversationMessageOutput":
        """Convert input to output schema using Pydantic 2+ model validation."""
        if created_at is None:
            created_at = datetime.now(UTC)

        # Use model_dump() to get all input data, then update with additional fields
        data = self.model_dump()
        data.update({"id": message_id, "created_at": created_at, "metadata": self.metadata})

        return ConversationMessageOutput.model_validate(data)


class ConversationMessageOutput(BaseModel):
    """Output schema for conversation messages."""

    id: UUID4 = Field(default_factory=uuid4, description="Unique message ID")
    session_id: UUID4 = Field(..., description="ID of the session")
    content: str = Field(..., description="Message content")
    role: MessageRole = Field(..., description="Role of the message sender")
    message_type: MessageType = Field(..., description="Type of message")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Creation timestamp")
    metadata: MessageMetadata | None = Field(default=None, description="Message metadata")
    token_count: int | None = Field(default=None, description="Token count for this message")
    execution_time: float | None = Field(default=None, description="Execution time in seconds")
    token_warning: dict[str, Any] | None = Field(default=None, description="Token usage warning if applicable")
    sources: list[dict[str, Any]] | None = Field(default=None, description="Source documents with full metadata")
    cot_output: dict[str, Any] | None = Field(default=None, description="Chain of Thought reasoning output")
    token_analysis: dict[str, Any] | None = Field(default=None, description="Detailed token usage breakdown")

    @classmethod
    def from_db_message(cls, message: Any) -> "ConversationMessageOutput":
        """Create ConversationMessageOutput from database message model.

        Reconstructs sources, cot_output, and token_analysis from stored metadata.
        """
        # Debug logging for token count extraction

        # Handle metadata properly - it's stored as a dict in the database
        metadata_value = None
        raw_metadata = None
        if message.message_metadata:
            if isinstance(message.message_metadata, dict):
                raw_metadata = message.message_metadata  # Keep reference to raw dict
                # It's already a dictionary from the database - convert to MessageMetadata object
                try:
                    metadata_value = MessageMetadata(**message.message_metadata)
                except (ValueError, KeyError, AttributeError) as e:
                    logger.error("Failed to create MessageMetadata from database dict: %s", str(e))
                    logger.error("Database metadata: %s", str(message.message_metadata))
                    metadata_value = None
            elif isinstance(message.message_metadata, MessageMetadata):
                # It's already a MessageMetadata object
                metadata_value = message.message_metadata
            else:
                logger.warning("Unexpected metadata type: %s", type(message.message_metadata))

        # Reconstruct token_analysis from metadata if available
        token_analysis = None
        if raw_metadata and "token_analysis" in raw_metadata:
            token_analysis = raw_metadata["token_analysis"]

        # Reconstruct sources from metadata if available
        # Note: Full source data (with scores, content, page numbers) needs to be stored in metadata
        # For now, we can only reconstruct if it was stored in metadata
        sources = None
        if raw_metadata and "sources" in raw_metadata:
            sources = raw_metadata["sources"]

        # Reconstruct cot_output from metadata if available
        cot_output = None
        if raw_metadata and "cot_output" in raw_metadata:
            cot_output = raw_metadata["cot_output"]

        data = {
            "id": message.id,
            "session_id": message.session_id,
            "content": message.content,
            "role": MessageRole(message.role),
            "message_type": MessageType(message.message_type),
            "created_at": message.created_at,
            "metadata": metadata_value,
            "token_count": message.token_count,
            "execution_time": message.execution_time,
            "token_analysis": token_analysis,
            "sources": sources,
            "cot_output": cot_output,
        }

        result = cls.model_validate(data)

        return result


class ContextMetadata(BaseModel):
    """Typed metadata for conversation context.

    Provides type-safe access to context metadata with validation.
    Replaces the untyped dict[str, Any] approach for better IDE support
    and runtime validation.
    """

    extracted_entities: list[str] = Field(
        default_factory=list, description="Named entities extracted from conversation (people, orgs, locations)"
    )
    conversation_topics: list[str] = Field(
        default_factory=list, description="Main topics identified in the conversation"
    )
    message_count: int = Field(default=0, ge=0, description="Number of messages used to build this context")
    context_length: int = Field(default=0, ge=0, description="Character length of the context window")

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class ConversationContext(BaseModel):
    """Schema for conversation context with typed metadata.

    Provides clean property-based access to commonly-used fields
    while maintaining backward compatibility.
    """

    session_id: UUID4 = Field(..., description="ID of the session")
    context_window: str = Field(..., min_length=1, max_length=50000, description="Current context window content")
    relevant_documents: list[str] = Field(default_factory=list, description="Relevant document IDs")
    metadata: ContextMetadata = Field(
        default_factory=ContextMetadata,
        description="Typed context metadata (entities, topics, counts)",
        alias="context_metadata",  # Backward compatibility
    )

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    # Properties for clean access to common metadata fields
    @property
    def entities(self) -> list[str]:
        """Get extracted entities from context.

        Returns:
            List of named entities (people, organizations, locations)
        """
        return self.metadata.extracted_entities

    @property
    def topics(self) -> list[str]:
        """Get conversation topics from context.

        Returns:
            List of identified conversation topics
        """
        return self.metadata.conversation_topics

    @property
    def message_count(self) -> int:
        """Get number of messages in context.

        Returns:
            Number of messages used to build this context
        """
        return self.metadata.message_count

    # Backward compatibility property
    @property
    def context_metadata(self) -> dict[str, Any]:
        """Get metadata as dict for backward compatibility.

        DEPRECATED: Use .metadata for typed access or .entities/.topics properties.

        Returns:
            Dictionary representation of context metadata
        """
        return {
            "extracted_entities": self.metadata.extracted_entities,
            "conversation_topics": self.metadata.conversation_topics,
            "message_count": self.metadata.message_count,
            "context_length": self.metadata.context_length,
        }


class ContextInput(BaseModel):
    """Input schema for context management."""

    session_id: UUID4 = Field(..., description="ID of the session")
    messages: list[ConversationMessageOutput] = Field(..., description="Messages to build context from")
    max_tokens: int = Field(default=2000, ge=500, le=4000, description="Maximum tokens in context")


class ContextOutput(BaseModel):
    """Output schema for context management."""

    context: ConversationContext = Field(..., description="Generated context")
    token_count: int = Field(..., ge=0, description="Number of tokens in context")
    entities: list[str] = Field(default_factory=list, description="Extracted entities")
    topics: list[str] = Field(default_factory=list, description="Identified topics")


class QuestionSuggestionInput(BaseModel):
    """Input schema for question suggestions."""

    session_id: UUID4 = Field(..., description="ID of the session")
    current_message: str = Field(..., description="Current message content")
    context: ConversationContext = Field(..., description="Current conversation context")
    max_suggestions: int = Field(default=3, ge=1, le=10, description="Maximum number of suggestions")


class QuestionSuggestionOutput(BaseModel):
    """Output schema for question suggestions."""

    suggestions: list[str] = Field(..., description="Suggested follow-up questions")
    confidence_scores: list[float] = Field(..., description="Confidence scores for suggestions")
    reasoning: str = Field(..., description="Reasoning for suggestions")


class ExportOutput(BaseModel):
    """Output schema for conversation export."""

    session_data: ConversationSessionOutput = Field(..., description="Session information")
    messages: list[ConversationMessageOutput] = Field(..., description="All messages in session")
    export_format: ExportFormat = Field(..., description="Format of the export")
    export_timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Export timestamp")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Export metadata")


class SessionStatistics(BaseModel):
    """Schema for session statistics."""

    session_id: UUID4 = Field(..., description="ID of the session")
    message_count: int = Field(..., ge=0, description="Total number of messages")
    user_messages: int = Field(..., ge=0, description="Number of user messages")
    assistant_messages: int = Field(..., ge=0, description="Number of assistant messages")
    total_tokens: int = Field(..., ge=0, description="Total tokens used")
    total_prompt_tokens: int = Field(default=0, ge=0, description="Total prompt tokens used")
    total_completion_tokens: int = Field(default=0, ge=0, description="Total completion tokens used")
    cot_usage_count: int = Field(default=0, ge=0, description="Number of times CoT was used")
    context_enhancement_count: int = Field(default=0, ge=0, description="Number of context enhancements")
    created_at: datetime = Field(..., description="Session creation time")
    last_activity: datetime = Field(..., description="Last activity time")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional statistics")


class SummarizationStrategy(str, Enum):
    """Strategy for conversation summarization."""

    RECENT_PLUS_SUMMARY = "recent_plus_summary"
    FULL_CONVERSATION = "full_conversation"
    KEY_POINTS_ONLY = "key_points_only"
    TOPIC_BASED = "topic_based"


class ConversationSummaryInput(BaseModel):
    """Input schema for creating conversation summaries."""

    session_id: UUID4 = Field(..., description="ID of the session to summarize")
    message_count_to_summarize: int = Field(..., ge=1, le=100, description="Number of messages to include in summary")
    strategy: SummarizationStrategy = Field(
        default=SummarizationStrategy.RECENT_PLUS_SUMMARY, description="Summarization strategy to use"
    )
    preserve_context: bool = Field(default=True, description="Whether to preserve important context")
    include_decisions: bool = Field(default=True, description="Whether to extract important decisions")
    include_questions: bool = Field(default=True, description="Whether to track unresolved questions")

    model_config = ConfigDict(extra="forbid")


class ConversationSummaryOutput(BaseModel):
    """Output schema for conversation summaries."""

    id: UUID4 = Field(default_factory=uuid4, description="Unique summary ID")
    session_id: UUID4 = Field(..., description="ID of the summarized session")
    summary_text: str = Field(..., min_length=1, description="Generated summary text")
    summarized_message_count: int = Field(..., ge=0, description="Number of messages summarized")
    tokens_saved: int = Field(..., ge=0, description="Estimated tokens saved by summarization")
    key_topics: list[str] = Field(default_factory=list, description="Key topics identified")
    important_decisions: list[str] = Field(default_factory=list, description="Important decisions made")
    unresolved_questions: list[str] = Field(default_factory=list, description="Questions still unresolved")
    summary_strategy: SummarizationStrategy = Field(..., description="Strategy used for summarization")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Summary creation timestamp")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional summary metadata")

    @classmethod
    def from_db_summary(cls, summary: Any) -> "ConversationSummaryOutput":
        """Create ConversationSummaryOutput from database summary model."""
        # Handle empty summary text with fallback
        summary_text = summary.summary_text
        if not summary_text or not summary_text.strip():
            summary_text = f"Summary for {summary.summarized_message_count} messages (auto-generated fallback)"

        return cls.model_validate(
            {
                "id": summary.id,
                "session_id": summary.session_id,
                "summary_text": summary_text,
                "summarized_message_count": summary.summarized_message_count,
                "tokens_saved": summary.tokens_saved,
                "key_topics": summary.key_topics,
                "important_decisions": summary.important_decisions,
                "unresolved_questions": summary.unresolved_questions,
                "summary_strategy": SummarizationStrategy(summary.summary_strategy),
                "created_at": summary.created_at,
                "metadata": summary.summary_metadata,
            }
        )


class SummarizationConfigInput(BaseModel):
    """Input schema for summarization configuration."""

    max_summary_length: int = Field(default=500, ge=100, le=2000, description="Maximum length of summary in tokens")
    context_window_threshold: float = Field(
        default=0.8, ge=0.5, le=1.0, description="Context window fill threshold to trigger summarization"
    )
    min_messages_for_summary: int = Field(
        default=10, ge=5, le=50, description="Minimum messages required before summarization"
    )
    preserve_recent_messages: int = Field(
        default=5, ge=2, le=20, description="Number of recent messages to preserve unsummarized"
    )
    topic_extraction_enabled: bool = Field(default=True, description="Whether to extract topics during summarization")
    decision_tracking_enabled: bool = Field(default=True, description="Whether to track important decisions")

    model_config = ConfigDict(extra="forbid")


class ContextSummarizationInput(BaseModel):
    """Input schema for context-aware summarization."""

    session_id: UUID4 = Field(..., description="ID of the session")
    messages: list[ConversationMessageOutput] = Field(..., min_length=1, description="Messages to summarize")
    config: SummarizationConfigInput = Field(
        default_factory=SummarizationConfigInput, description="Summarization configuration"
    )
    current_context_size: int = Field(..., ge=0, description="Current context window size in tokens")
    target_context_size: int = Field(..., ge=500, description="Target context window size after summarization")

    model_config = ConfigDict(extra="forbid")


class ContextSummarizationOutput(BaseModel):
    """Output schema for context-aware summarization."""

    summary: ConversationSummaryOutput = Field(..., description="Generated summary")
    preserved_messages: list[ConversationMessageOutput] = Field(
        ..., description="Messages preserved without summarization"
    )
    tokens_saved: int = Field(..., ge=0, description="Total tokens saved")
    new_context_size: int = Field(..., ge=0, description="New context size after summarization")
    compression_ratio: float = Field(..., ge=0.0, description="Compression ratio achieved")

    model_config = ConfigDict(extra="forbid")


class ConversationSuggestionInput(BaseModel):
    """Input schema for conversation-based question suggestions."""

    session_id: UUID4 = Field(..., description="ID of the session")
    collection_id: UUID4 = Field(..., description="ID of the collection")
    last_message: str = Field(..., min_length=1, description="Last message in conversation")
    conversation_context: str = Field(default="", description="Summarized conversation context")
    max_suggestions: int = Field(default=3, ge=1, le=10, description="Maximum number of suggestions to generate")
    suggestion_types: list[str] = Field(
        default_factory=lambda: ["follow_up", "clarification", "related"],
        description="Types of suggestions to generate",
    )
    include_document_based: bool = Field(default=True, description="Whether to include document-based suggestions")

    model_config = ConfigDict(extra="forbid")


class ConversationSuggestionOutput(BaseModel):
    """Output schema for conversation-based question suggestions."""

    suggestions: list[str] = Field(..., description="Generated question suggestions")
    suggestion_types: list[str] = Field(..., description="Type of each suggestion")
    confidence_scores: list[float] = Field(..., description="Confidence scores for each suggestion (0.0-1.0)")
    context_relevance: list[float] = Field(..., description="Context relevance scores for each suggestion (0.0-1.0)")
    document_sources: list[list[str]] = Field(default_factory=list, description="Document sources for each suggestion")
    reasoning: str = Field(..., description="Reasoning for the generated suggestions")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional suggestion metadata")

    @field_validator("confidence_scores", "context_relevance")
    @classmethod
    def validate_scores(cls, v: list[float]) -> list[float]:
        """Validate that all scores are between 0.0 and 1.0."""
        for score in v:
            if not 0.0 <= score <= 1.0:
                raise ValueError(f"Score {score} must be between 0.0 and 1.0")
        return v

    model_config = ConfigDict(extra="forbid")


class ConversationExportInput(BaseModel):
    """Input schema for conversation export."""

    session_id: UUID4 = Field(..., description="ID of the session to export")
    format: ExportFormat = Field(..., description="Export format")
    include_metadata: bool = Field(default=True, description="Whether to include message metadata")
    include_timestamps: bool = Field(default=True, description="Whether to include timestamps")
    include_token_counts: bool = Field(default=False, description="Whether to include token counts")
    include_summaries: bool = Field(default=True, description="Whether to include conversation summaries")
    date_range_start: datetime | None = Field(default=None, description="Start date for filtering messages")
    date_range_end: datetime | None = Field(default=None, description="End date for filtering messages")
    custom_fields: list[str] = Field(default_factory=list, description="Custom fields to include in export")

    @field_validator("date_range_end")
    @classmethod
    def validate_date_range(cls, v: datetime | None, info: Any) -> datetime | None:
        """Validate that end date is after start date."""
        if v is not None and info.data.get("date_range_start") is not None and v <= info.data["date_range_start"]:
            raise ValueError("End date must be after start date")
        return v

    model_config = ConfigDict(extra="forbid")


class ConversationExportOutput(BaseModel):
    """Output schema for conversation export."""

    session_data: ConversationSessionOutput = Field(..., description="Session information")
    messages: list[ConversationMessageOutput] = Field(..., description="Exported messages")
    summaries: list[ConversationSummaryOutput] = Field(default_factory=list, description="Conversation summaries")
    export_format: ExportFormat = Field(..., description="Format of the export")
    export_timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Export timestamp")
    total_messages: int = Field(..., ge=0, description="Total number of messages exported")
    total_tokens: int = Field(default=0, ge=0, description="Total tokens in exported content")
    file_size_bytes: int = Field(default=0, ge=0, description="Size of exported file in bytes")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Export metadata and statistics")

    model_config = ConfigDict(extra="forbid")
