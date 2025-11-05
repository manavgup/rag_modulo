"""Collection model for RAG solution database."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, ClassVar

from sqlalchemy import Boolean, DateTime, Enum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.identity_service import IdentityService
from rag_solution.file_management.database import Base
from rag_solution.schemas.collection_schema import CollectionStatus

if TYPE_CHECKING:
    from rag_solution.models.conversation import ConversationSession
    from rag_solution.models.file import File
    from rag_solution.models.podcast import Podcast
    from rag_solution.models.question import SuggestedQuestion
    from rag_solution.models.user_collection import UserCollection


class Collection(Base):  # pylint: disable=too-few-public-methods
    """
    Represents a collection entity that groups resources and configurations.
    """

    __tablename__ = "collections"
    __table_args__: ClassVar[dict] = {"extend_existing": True}

    # 🆔 Identification
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=IdentityService.generate_id)

    # ⚙️ Core Attributes
    name: Mapped[str] = mapped_column(String, index=True)
    vector_db_name: Mapped[str] = mapped_column(
        String, nullable=False
    )  # Name of the collection in the vector database (e.g., Milvus)
    status: Mapped[CollectionStatus] = mapped_column(
        Enum(CollectionStatus, name="collectionstatus", create_type=False), default=CollectionStatus.CREATED
    )

    # 🟢 Flags
    is_private: Mapped[bool] = mapped_column(Boolean, default=False)

    # 📊 Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # 🔗 Relationships
    files: Mapped[list[File]] = relationship("File", back_populates="collection", lazy="selectin")
    users: Mapped[list[UserCollection]] = relationship("UserCollection", back_populates="collection", lazy="selectin")
    suggested_questions: Mapped[list[SuggestedQuestion]] = relationship(
        "SuggestedQuestion", back_populates="collection", cascade="all, delete-orphan"
    )
    conversation_sessions: Mapped[list[ConversationSession]] = relationship(
        "ConversationSession", back_populates="collection", cascade="all, delete-orphan"
    )
    podcasts: Mapped[list["Podcast"]] = relationship(
        "Podcast", back_populates="collection", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"Collection(id='{self.id}', name='{self.name}', is_private={self.is_private})"

    def is_accessible_by_user(self, user_id: uuid.UUID) -> bool:
        """Check if a user has access to this collection."""
        return not self.is_private or any(user_collection.user_id == user_id for user_collection in self.users)
