"""DEPRECATED: This file will be removed in Phase 7.

Use rag_solution.models.conversation.ConversationMessage instead.
This file is maintained for backward compatibility during Phases 3-6.
"""

import uuid
import warnings
from datetime import UTC, datetime
from typing import ClassVar

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.identity_service import IdentityService
from rag_solution.file_management.database import Base

# Issue deprecation warning when this module is imported
warnings.warn(
    "conversation_message.py is deprecated and will be removed in Phase 7. "
    "Use rag_solution.models.conversation.ConversationMessage instead.",
    DeprecationWarning,
    stacklevel=2,
)


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"
    __table_args__: ClassVar[dict] = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=IdentityService.generate_id)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversation_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)  # user, assistant, system
    message_type: Mapped[str] = mapped_column(String(50), nullable=False)  # question, answer, follow_up, etc.
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    message_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    execution_time: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    session = relationship("ConversationSession", back_populates="messages")

    def __repr__(self) -> str:
        return f"<ConversationMessage(id={self.id}, role='{self.role}', type='{self.message_type}')>"
