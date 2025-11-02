"""DEPRECATED: This file will be removed in Phase 7.

Use rag_solution.models.conversation.ConversationSummary instead.
This file is maintained for backward compatibility during Phases 3-6.
"""

import uuid
import warnings
from datetime import UTC, datetime
from typing import TYPE_CHECKING, ClassVar

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.identity_service import IdentityService
from rag_solution.file_management.database import Base

# Issue deprecation warning when this module is imported
warnings.warn(
    "conversation_summary.py is deprecated and will be removed in Phase 7. "
    "Use rag_solution.models.conversation.ConversationSummary instead.",
    DeprecationWarning,
    stacklevel=2,
)

if TYPE_CHECKING:
    from rag_solution.models.conversation_session import ConversationSession


class ConversationSummary(Base):
    """Model for storing conversation summaries to manage context windows."""

    __tablename__ = "conversation_summaries"
    __table_args__: ClassVar[dict] = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=IdentityService.generate_id)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversation_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    summarized_message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_saved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    key_topics: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    important_decisions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    unresolved_questions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    summary_strategy: Mapped[str] = mapped_column(String(50), nullable=False, default="recent_plus_summary")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    summary_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Relationships
    session: Mapped["ConversationSession"] = relationship("ConversationSession", back_populates="summaries")

    def __repr__(self) -> str:
        """Return string representation of the conversation summary."""
        return (
            f"<ConversationSummary(id={self.id}, session_id={self.session_id}, "
            f"messages={self.summarized_message_count})>"
        )
