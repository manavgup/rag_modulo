"""Database model for conversation summaries."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from core.identity_service import IdentityService
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from rag_solution.file_management.database import Base

if TYPE_CHECKING:
    from rag_solution.models.conversation_session import ConversationSession


class ConversationSummary(Base):
    """Model for storing conversation summaries to manage context windows."""

    __tablename__ = "conversation_summaries"

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
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    summary_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Relationships
    session: Mapped["ConversationSession"] = relationship("ConversationSession", back_populates="summaries")

    def __repr__(self) -> str:
        """Return string representation of the conversation summary."""
        return (
            f"<ConversationSummary(id={self.id}, session_id={self.session_id}, "
            f"messages={self.summarized_message_count})>"
        )
