from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from rag_solution.file_management.database import Base

if TYPE_CHECKING:
    from rag_solution.models.llm_provider import LLMProvider


class PipelineConfig(Base):
    """Model representing a Pipeline Configuration for a RAG pipeline."""

    __tablename__ = "pipeline_configs"

    # Identifiers
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[UUID] = mapped_column(  # Add user ownership
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    collection_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("collections.id", ondelete="CASCADE"), nullable=True, index=True
    )

    # Core Pipeline Settings
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    chunking_strategy: Mapped[str] = mapped_column(String(50), nullable=False, default="fixed")
    embedding_model: Mapped[str] = mapped_column(String(255), nullable=False)
    retriever: Mapped[str] = mapped_column(String(50), nullable=False, default="vector")
    context_strategy: Mapped[str] = mapped_column(String(50), nullable=False, default="priority")
    enable_logging: Mapped[bool] = mapped_column(Boolean, default=True)

    # Advanced Configuration
    max_context_length: Mapped[int | None] = mapped_column(Integer, nullable=True, default=2048)
    timeout: Mapped[float | None] = mapped_column(Float, nullable=True, default=30.0)
    config_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    # Provider reference
    provider_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("llm_providers.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[LLMProvider] = relationship("LLMProvider", lazy="selectin")

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self) -> str:
        return f"<PipelineConfig(id={self.id}, name='{self.name}', collection_id={self.collection_id})>"
