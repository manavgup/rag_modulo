import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from rag_solution.file_management.database import Base
from rag_solution.schemas.prompt_template_schema import PromptTemplateType

if TYPE_CHECKING:
    from rag_solution.models.user import User


class PromptTemplate(Base):
    """SQLAlchemy model for Prompt Templates."""

    __tablename__ = "prompt_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=False)
    __table_args__ = (UniqueConstraint("name", "user_id", name="uix_name_user"),)
    template_type: Mapped[PromptTemplateType] = mapped_column(
        SQLAlchemyEnum(PromptTemplateType, name="prompttemplatetype", create_type=False), nullable=False
    )
    system_prompt: Mapped[str | None] = mapped_column(
        Text, nullable=True, server_default="You are a helpful AI assistant."
    )
    template_format: Mapped[str] = mapped_column(Text, nullable=False)
    input_variables: Mapped[dict] = mapped_column(JSON, nullable=False)  # Store as JSON
    example_inputs: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # Store as JSON
    context_strategy: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # Store as JSON
    max_context_length: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stop_sequences: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # Store as JSON
    validation_schema: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # Store as JSON
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="prompt_templates")

    def __repr__(self) -> str:
        return f"<PromptTemplate(id={self.id}, name='{self.name}', user_id={self.user_id})>"
