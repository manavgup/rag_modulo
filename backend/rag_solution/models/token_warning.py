"""Token warning model for persisting token usage warnings."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from core.identity_service import IdentityService
from rag_solution.file_management.database import Base


class TokenWarning(Base):
    """Model for storing token usage warnings in the database.

    This model persists token warnings that are generated when users
    approach or exceed token limits for their LLM usage.
    """

    __tablename__ = "token_warnings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=IdentityService.generate_id
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    session_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    warning_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    current_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    limit_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    percentage_used: Mapped[float] = mapped_column(Float, nullable=False)
    message: Mapped[str] = mapped_column(String(1000), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    suggested_action: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    service_type: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        """String representation of TokenWarning."""
        return (
            f"<TokenWarning(id={self.id}, type='{self.warning_type}', "
            f"severity='{self.severity}', tokens={self.current_tokens}/{self.limit_tokens})>"
        )
