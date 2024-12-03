from __future__ import annotations

import uuid
from sqlalchemy import String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from rag_solution.file_management.database import Base

class SuggestedQuestion(Base):
    """Model for storing suggested questions for collections."""
    __tablename__ = "suggested_questions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    collection_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("collections.id", ondelete="CASCADE"))
    question: Mapped[str] = mapped_column(String, nullable=False)

    # Relationship to Collection
    collection: Mapped["Collection"] = relationship("Collection", back_populates="suggested_questions")

    def __repr__(self):
        return f"SuggestedQuestion(id='{self.id}', question='{self.question}')"
