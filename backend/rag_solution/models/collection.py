from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from rag_solution.file_management.database import Base
from rag_solution.schemas.collection_schema import CollectionStatus

class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, index=True)
    vector_db_name: Mapped[str] = mapped_column(String, nullable=False)
    is_private: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[CollectionStatus] = mapped_column(
        Enum(CollectionStatus, name='collectionstatus', create_type=False),
        default=CollectionStatus.CREATED
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    files: Mapped[list['File']] = relationship("File", back_populates="collection", lazy="selectin")
    users: Mapped[list['UserCollection']] = relationship("UserCollection", back_populates="collection")
    suggested_questions: Mapped[list['SuggestedQuestion']] = relationship("SuggestedQuestion", back_populates="collection", cascade="all, delete-orphan")

    def __repr__(self):
        return f"Collection(id='{self.id}', name='{self.name}', is_private={self.is_private})"
