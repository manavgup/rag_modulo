import uuid

from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from rag_solution.file_management.database import Base


class LLMProvider(Base):
    __tablename__ = "llm_providers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name = Column(String(255), nullable=False, unique=True)
    base_url = Column(String(1024), nullable=False)
    api_key = Column(String(1024), nullable=False)
    org_id = Column(String(255), nullable=True)
    project_id = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    is_default = Column(Boolean, nullable=False, default=False, server_default="false")

    models = relationship("LLMModel", back_populates="provider")

    def __repr__(self) -> str:
        return f"<LLMProvider(id={self.id}, name='{self.name}', active={self.is_active})>"
