from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from rag_solution.file_management.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ibm_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    email: Mapped[str] = mapped_column(String, index=True)
    name: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String, default="user")
    preferred_provider_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("llm_providers.id", ondelete="SET NULL"), 
        nullable=True
    )  
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Add cascade="all, delete-orphan" to relationships where User is the parent
    teams = relationship("UserTeam", back_populates="user", cascade="all, delete-orphan")
    collections = relationship("UserCollection", back_populates="user", cascade="all, delete-orphan")
    files = relationship("File", back_populates="user", cascade="all, delete-orphan")
    llm_parameters = relationship("LLMParameters", back_populates="user", cascade="all, delete-orphan")
    prompt_templates = relationship("PromptTemplate", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"User(id='{self.id}', ibm_id='{self.ibm_id}', email='{self.email}', name='{self.name}', role='{self.role}')"
