from __future__ import annotations
from sqlalchemy import String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from ..file_management.database import Base
from .associations import user_collection_association

# ... rest of the file remains the same
class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, index=True)
    is_private: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    files: Mapped[list["File"]] = relationship("File", back_populates="collection")  # Use string literal for type hint
    users: Mapped[list["User"]] = relationship("User", secondary=user_collection_association, back_populates="collections")

    def __repr__(self):
        return f"Collection(id='{self.id}'\
                name='{self.name}',\
                is_private={self.is_private})"
