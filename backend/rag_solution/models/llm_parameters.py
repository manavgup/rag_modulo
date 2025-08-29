import uuid
from datetime import datetime

from pydantic import field_validator
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from rag_solution.file_management.database import Base


class LLMParameters(Base):
    """
    Model for storing LLM generation parameters for a collection.
    """

    __tablename__ = "llm_parameters"

    # 🆔 Identification
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # ⚙️ Core LLM Parameters
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    max_new_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    temperature: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)
    top_k: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    top_p: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    repetition_penalty: Mapped[float | None] = mapped_column(Float, nullable=True, default=1.1)

    # 🟢 Status Flags
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)

    # 📊 Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # 🔗 Relationships
    user: Mapped["User"] = relationship("User", back_populates="llm_parameters", lazy="selectin")

    @field_validator("user_id")
    @classmethod
    def validate_uuid(cls, v):
        if not isinstance(v, UUID):
            try:
                return UUID(v)
            except ValueError:
                raise ValueError("Invalid UUID format")
        return v

    def __repr__(self):
        return f"<LLMParameters(id={self.id}, name='{self.name}', is_default={self.is_default})>"
