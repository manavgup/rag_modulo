from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, Float, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from rag_solution.file_management.database import Base
from rag_solution.schemas.llm_provider_schema import ModelType


class LLMProvider(Base):
    __tablename__ = "llm_providers"
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    base_url = Column(String(1024), nullable=False)
    api_key = Column(String(1024), nullable=False)
    org_id = Column(String(255), nullable=True)
    project_id = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    is_default = Column(Boolean, nullable=False, default=False)
    
    models = relationship("LLMProviderModel", back_populates="provider")

    def __repr__(self) -> str:
        return f"<LLMProvider(id={self.id}, name='{self.name}', active={self.is_active})>"


class LLMProviderModel(Base):
    __tablename__ = "llm_provider_models"
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    provider_id = Column(UUID(as_uuid=True), ForeignKey("llm_providers.id"), nullable=False)
    model_id = Column(String(255), nullable=False, index=True)
    default_model_id = Column(String(255), nullable=False)
    model_type = Column(Enum(ModelType, name='llm_model_type', native_enum=True), nullable=False, default=ModelType.GENERATION)
    
    # Runtime Settings
    timeout = Column(Integer, nullable=False, default=30)
    max_retries = Column(Integer, nullable=False, default=3)
    batch_size = Column(Integer, nullable=False, default=10)
    retry_delay = Column(Float, nullable=False, default=1.0)
    concurrency_limit = Column(Integer, nullable=False, default=10)
    stream = Column(Boolean, nullable=False, default=False)
    rate_limit = Column(Integer, nullable=False, default=10)
    
    # State
    is_default = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    provider = relationship("LLMProvider", back_populates="models")

    def __repr__(self) -> str:
        return f"<LLMProviderModel(id={self.id}, model='{self.model_id}', type='{self.model_type}', active={self.is_active})>"
