from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from rag_solution.file_management.database import Base

if TYPE_CHECKING:
    from rag_solution.models.conversation_session import ConversationSession
    from rag_solution.models.file import File
    from rag_solution.models.llm_parameters import LLMParameters
    from rag_solution.models.prompt_template import PromptTemplate
    from rag_solution.models.user_collection import UserCollection
    from rag_solution.models.user_team import UserTeam


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ibm_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    email: Mapped[str] = mapped_column(String, index=True)
    name: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String, default="user")
    preferred_provider_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("llm_providers.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Add cascade="all, delete-orphan" to relationships where User is the parent
    teams: Mapped[list[UserTeam]] = relationship("UserTeam", back_populates="user", cascade="all, delete-orphan")
    collections: Mapped[list[UserCollection]] = relationship(
        "UserCollection", back_populates="user", cascade="all, delete-orphan"
    )
    files: Mapped[list[File]] = relationship("File", back_populates="user", cascade="all, delete-orphan")
    llm_parameters: Mapped[list[LLMParameters]] = relationship(
        "LLMParameters", back_populates="user", cascade="all, delete-orphan"
    )
    prompt_templates: Mapped[list[PromptTemplate]] = relationship(
        "PromptTemplate", back_populates="user", cascade="all, delete-orphan"
    )
    conversation_sessions: Mapped[list[ConversationSession]] = relationship(
        "ConversationSession", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"User(id='{self.id}', ibm_id='{self.ibm_id}', "
            f"email='{self.email}', name='{self.name}', role='{self.role}')"
        )
