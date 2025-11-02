"""Unified conversation models for Chat with Documents feature.

This module consolidates ConversationSession, ConversationMessage, and ConversationSummary
into a single file with proper relationships and eager loading support.

Consolidation Benefits:
- Reduces 3 files (137 lines) to 1 file
- Improves code maintainability and discoverability
- Better relationship management in one place
- Easier to understand data model hierarchy
"""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, ClassVar

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.identity_service import IdentityService
from rag_solution.file_management.database import Base

if TYPE_CHECKING:
    from rag_solution.models.collection import Collection
    from rag_solution.models.user import User


class ConversationSession(Base):
    """Model for conversation sessions.

    Represents a conversation session between a user and the RAG system,
    tied to a specific collection. Sessions maintain context window settings,
    message limits, and archival status.

    Attributes:
        id: Unique session identifier
        user_id: Foreign key to User who owns this session
        collection_id: Foreign key to Collection being queried
        session_name: Human-readable name for the session
        status: Current status (active, paused, archived, expired, deleted)
        context_window_size: Maximum context window size in tokens
        max_messages: Maximum number of messages to keep
        is_archived: Whether session is archived
        is_pinned: Whether session is pinned to top
        created_at: Session creation timestamp
        updated_at: Last update timestamp
        session_metadata: Additional metadata as JSON
    """

    __tablename__ = "conversation_sessions"
    __table_args__: ClassVar[dict] = {"extend_existing": True}

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=IdentityService.generate_id)

    # Foreign keys
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    collection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("collections.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Session configuration
    session_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    context_window_size: Mapped[int] = mapped_column(Integer, nullable=False, default=4000)
    max_messages: Mapped[int] = mapped_column(Integer, nullable=False, default=50)

    # Session flags
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    # Metadata
    session_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="conversation_sessions")
    collection: Mapped["Collection"] = relationship("Collection", back_populates="conversation_sessions")
    messages: Mapped[list["ConversationMessage"]] = relationship(
        "ConversationMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ConversationMessage.created_at",
        lazy="select",  # Changed from default to support eager loading in repository
    )
    summaries: Mapped[list["ConversationSummary"]] = relationship(
        "ConversationSummary",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ConversationSummary.created_at",
        lazy="select",
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<ConversationSession(id={self.id}, name='{self.session_name}', status='{self.status}')>"


class ConversationMessage(Base):
    """Model for individual messages in a conversation.

    Represents a single message exchange in a conversation session.
    Messages can be from user, assistant, or system roles.

    Attributes:
        id: Unique message identifier
        session_id: Foreign key to ConversationSession
        content: The message text content
        role: Message role (user, assistant, system)
        message_type: Type of message (question, answer, follow_up, etc.)
        created_at: Message creation timestamp
        message_metadata: Additional metadata as JSON
        token_count: Number of tokens in message (nullable)
        execution_time: Processing time in seconds (nullable)
    """

    __tablename__ = "conversation_messages"
    __table_args__: ClassVar[dict] = {"extend_existing": True}

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=IdentityService.generate_id)

    # Foreign key
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversation_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Message content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)  # user, assistant, system
    message_type: Mapped[str] = mapped_column(String(50), nullable=False)  # question, answer, follow_up, etc.

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(UTC))

    # Metadata and metrics
    message_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    execution_time: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    session: Mapped["ConversationSession"] = relationship("ConversationSession", back_populates="messages")

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<ConversationMessage(id={self.id}, role='{self.role}', type='{self.message_type}')>"


class ConversationSummary(Base):
    """Model for conversation summaries to manage context windows.

    Stores summaries of conversation sessions to help manage context window limits.
    Summaries track key topics, decisions, and unresolved questions.

    Attributes:
        id: Unique summary identifier
        session_id: Foreign key to ConversationSession
        summary_text: The summary text
        summarized_message_count: Number of messages summarized
        tokens_saved: Number of tokens saved by summarization
        key_topics: List of key topics discussed
        important_decisions: List of important decisions made
        unresolved_questions: List of unresolved questions
        summary_strategy: Strategy used for summarization
        created_at: Summary creation timestamp
        summary_metadata: Additional metadata as JSON
    """

    __tablename__ = "conversation_summaries"
    __table_args__: ClassVar[dict] = {"extend_existing": True}

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=IdentityService.generate_id)

    # Foreign key
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversation_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Summary content
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Summary metrics
    summarized_message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_saved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Structured summary data
    key_topics: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    important_decisions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    unresolved_questions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    # Summary configuration
    summary_strategy: Mapped[str] = mapped_column(String(50), nullable=False, default="recent_plus_summary")

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(UTC))

    # Metadata
    summary_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Relationships
    session: Mapped["ConversationSession"] = relationship("ConversationSession", back_populates="summaries")

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<ConversationSummary(id={self.id}, session_id={self.session_id}, "
            f"messages={self.summarized_message_count})>"
        )
