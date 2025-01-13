import uuid
from datetime import datetime
from typing import Optional, Dict, List
from enum import Enum as PyEnum, auto
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy import String, Boolean, DateTime, Text, ForeignKey, Enum, Integer
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from rag_solution.file_management.database import Base


# 🟢 Enum for Prompt Types
class PromptTemplateType(str, PyEnum):
    """Enum for prompt template types that matches schema values."""
    RAG_QUERY = "RAG_QUERY"
    QUESTION_GENERATION = "QUESTION_GENERATION"
    RESPONSE_EVALUATION = "RESPONSE_EVALUATION"
    CUSTOM = "CUSTOM"


# 🟢 Enum for Context Strategies
class ContextStrategyType(PyEnum):
    CONCATENATE = auto()
    SUMMARIZE = auto()
    TRUNCATE = auto()
    PRIORITY = auto()

    @property
    def value(self) -> str:
        """Get string value for the enum."""
        return self.name.lower()


class PromptTemplate(Base):
    """Model for flexible and dynamic prompt templates."""
    __tablename__ = "prompt_templates"

    # 🆔 Identification
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # ⚙️ Core Template Attributes
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    template_type: Mapped[PromptTemplateType] = mapped_column(
        Enum(PromptTemplateType, name="prompt_template_type"),
        default=PromptTemplateType.CUSTOM,
        nullable=False
    )
    system_prompt: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, default=None
    )
    template_format: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Format string with placeholders like {context}, {question}"
    )
    input_variables: Mapped[Optional[Dict[str, str]]] = mapped_column(
        JSON, nullable=True,
        comment="Key-value pairs describing variables used in template_format"
    )
    example_inputs: Mapped[Optional[Dict]] = mapped_column(
        JSON, nullable=True,
        comment="Example inputs demonstrating template usage"
    )

    # 🛠️ Advanced Context Handling
    context_strategy: Mapped[Optional[Dict]] = mapped_column(
        JSON, nullable=True,
        comment="Strategy for handling context chunks"
    )
    max_context_length: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True,
        comment="Maximum context length in tokens"
    )
    stop_sequences: Mapped[Optional[List[str]]] = mapped_column(
        JSON, nullable=True,
        comment="List of stop sequences for generation"
    )
    validation_schema: Mapped[Optional[Dict]] = mapped_column(
        JSON, nullable=True,
        comment="Schema for validating template variables"
    )

    # 🟢 Status Flags
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # 📊 Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # 🔗 Relationships
    user: Mapped["User"] = relationship(
        "User", back_populates="prompt_templates", lazy="selectin"
    )

    def __repr__(self):
        return (
            f"<PromptTemplate(id={self.id}, name='{self.name}', provider='{self.provider}', "
            f"type='{self.template_type}', is_default={self.is_default})>"
        )