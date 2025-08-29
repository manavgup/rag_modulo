import uuid

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from rag_solution.file_management.database import Base
from rag_solution.schemas.prompt_template_schema import PromptTemplateType


class PromptTemplate(Base):
    """SQLAlchemy model for Prompt Templates."""

    __tablename__ = "prompt_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False, unique=False)
    __table_args__ = (UniqueConstraint("name", "user_id", name="uix_name_user"),)
    template_type = Column(
        SQLAlchemyEnum(PromptTemplateType, name="prompttemplatetype", create_type=False), nullable=False
    )
    system_prompt = Column(Text, nullable=True, server_default="You are a helpful AI assistant.")
    template_format = Column(Text, nullable=False)
    input_variables = Column(JSON, nullable=False)  # Store as JSON
    example_inputs = Column(JSON, nullable=True)  # Store as JSON
    context_strategy = Column(JSON, nullable=True)  # Store as JSON
    max_context_length = Column(Integer, nullable=True)
    stop_sequences = Column(JSON, nullable=True)  # Store as JSON
    validation_schema = Column(JSON, nullable=True)  # Store as JSON
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="prompt_templates")

    def __repr__(self) -> str:
        return f"<PromptTemplate(id={self.id}, name='{self.name}', provider_id={self.provider_id})>"
