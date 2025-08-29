import uuid

from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from rag_solution.file_management.database import Base
from rag_solution.schemas.llm_model_schema import ModelType


class LLMModel(Base):
    __tablename__ = "llm_models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    provider_id = Column(UUID(as_uuid=True), ForeignKey("llm_providers.id", ondelete="CASCADE"), nullable=False)
    model_id = Column(String(255), nullable=False, index=True)
    default_model_id = Column(String(255), nullable=False)
    model_type = Column(Enum(ModelType, name="llm_model_type", native_enum=True), nullable=False)

    # Runtime Settings
    timeout = Column(Integer, nullable=False, default=30)
    max_retries = Column(Integer, nullable=False, default=3)
    batch_size = Column(Integer, nullable=False, default=10)
    retry_delay = Column(Float, nullable=False, default=1.0)
    concurrency_limit = Column(Integer, nullable=False, default=10)
    stream = Column(Boolean, nullable=False, default=False)
    rate_limit = Column(Integer, nullable=False, default=10)

    is_default = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    provider = relationship("LLMProvider", back_populates="models")

    def __repr__(self) -> str:
        return f"<LLMModel(id={self.id}, model='{self.model_id}', type='{self.model_type}', active={self.is_active})>"
