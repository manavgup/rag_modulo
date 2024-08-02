from __future__ import annotations
from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from ..file_management.database import Base

class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, index=True)
    vector_db_name = mapped_column(String, nullable=False) 
    is_private: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    files: Mapped[list['File']] = relationship("File", back_populates="collection", lazy="selectin")
    users: Mapped[list['UserCollection']] = relationship("UserCollection", back_populates="collection")

    def __repr__(self):
        return f"Collection(id='{self.id}', name='{self.name}', is_private={self.is_private})"
