"""SQLAlchemy model for suggested questions."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, ClassVar

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.identity_service import IdentityService
from rag_solution.file_management.database import Base

if TYPE_CHECKING:
    from rag_solution.models.collection import Collection


class SuggestedQuestion(Base):
    """Model for storing suggested questions for collections.

    Attributes:
        id: Unique identifier for the question
        collection_id: ID of the collection this question belongs to
        question: The question text
        created_at: Timestamp when the question was created
        metadata: Optional JSON metadata for the question
        collection: Relationship to the parent Collection
    """

    __tablename__ = "suggested_questions"
    __table_args__: ClassVar[dict] = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=IdentityService.generate_id,
        doc="Unique identifier for the question",
    )
    collection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("collections.id", ondelete="CASCADE"),
        nullable=False,
        doc="ID of the collection this question belongs to",
    )
    question: Mapped[str] = mapped_column(
        String(500),  # Match schema max_length
        nullable=False,
        doc="The question text",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Timestamp when the question was created",
    )
    question_metadata: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, default=None, doc="Optional JSON metadata for the question"
    )

    # Relationship to Collection
    collection: Mapped[Collection] = relationship(
        "Collection", back_populates="suggested_questions", doc="Relationship to the parent Collection"
    )

    def __repr__(self) -> str:
        """String representation of the question."""
        return f"SuggestedQuestion(id='{self.id}', collection_id='{self.collection_id}', question='{self.question}')"

    @property
    def is_valid(self) -> bool:
        """Check if the question meets basic validation rules."""
        if not self.question:
            return False
        question = self.question.strip()
        return len(question) >= 10 and len(question) <= 500 and question.endswith("?")
