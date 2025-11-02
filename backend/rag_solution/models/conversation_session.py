"""DEPRECATED: This file will be removed in Phase 7.

Use rag_solution.models.conversation.ConversationSession instead.
This file is maintained for backward compatibility during Phases 3-6.
"""

import uuid
import warnings
from datetime import UTC, datetime
from typing import ClassVar

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.identity_service import IdentityService
from rag_solution.file_management.database import Base

# Issue deprecation warning when this module is imported
warnings.warn(
    "conversation_session.py is deprecated and will be removed in Phase 7. "
    "Use rag_solution.models.conversation.ConversationSession instead.",
    DeprecationWarning,
    stacklevel=2,
)


class ConversationSession(Base):
    __tablename__ = "conversation_sessions"
    __table_args__: ClassVar[dict] = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=IdentityService.generate_id)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    collection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("collections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    context_window_size: Mapped[int] = mapped_column(Integer, nullable=False, default=4000)
    max_messages: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )
    session_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Relationships
    user = relationship("User", back_populates="conversation_sessions")
    collection = relationship("Collection", back_populates="conversation_sessions")
    messages = relationship(
        "ConversationMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ConversationMessage.created_at",
    )
    summaries = relationship(
        "ConversationSummary",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ConversationSummary.created_at",
    )

    def __repr__(self) -> str:
        return f"<ConversationSession(id={self.id}, name='{self.session_name}', status='{self.status}')>"
