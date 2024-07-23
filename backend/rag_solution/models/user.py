from __future__ import annotations
from sqlalchemy import String, DateTime, Table, Column, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from ..file_management.database import Base
from .associations import user_team_association, user_collection_association

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ibm_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    collections: Mapped[list["Collection"]] = relationship("Collection", secondary=user_collection_association, back_populates="users")
    teams: Mapped[list["Team"]] = relationship("Team", secondary=user_team_association, back_populates="users")

    def __repr__(self):
        return f"User(id='{self.id}', ibm_id='{self.ibm_id}', email='{self.email}', name='{self.name}')"

# Move this import to the end of the file to avoid circular imports
from .collection import Collection