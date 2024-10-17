from __future__ import annotations

import uuid
from typing import Optional
from datetime import datetime

from sqlalchemy import DateTime, String, Text, Integer, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from rag_solution.file_management.database import Base


class Assistant(Base):
    __tablename__ = "assistants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query: Mapped[str] = mapped_column(Text)
    context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    max_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return (
            f"Assistant(id='{self.id}', query='{self.query}', "
            f"context={self.context}, max_tokens={self.max_tokens}, "
            f"response={self.response}, confidence={self.confidence}, "
            f"error={self.error}, user_id={self.user_id}, "
        )

