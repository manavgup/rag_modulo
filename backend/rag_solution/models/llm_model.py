import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from rag_solution.file_management.database import Base
from rag_solution.schemas.llm_model_schema import ModelType

if TYPE_CHECKING:
    from rag_solution.models.llm_provider import LLMProvider


class LLMModel(Base):
    __tablename__ = "llm_models"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    provider_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("llm_providers.id", ondelete="CASCADE"), nullable=False)
    model_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    default_model_id: Mapped[str] = mapped_column(String(255), nullable=False)
    model_type: Mapped[ModelType] = mapped_column(Enum(ModelType, name="llm_model_type", native_enum=True), nullable=False)

    # Runtime Settings
    timeout: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    batch_size: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    retry_delay: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    concurrency_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    stream: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rate_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=10)

    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    provider: Mapped["LLMProvider"] = relationship("LLMProvider", back_populates="models")

    def __repr__(self) -> str:
        return f"<LLMModel(id={self.id}, model='{self.model_id}', type='{self.model_type}', active={self.is_active})>"
