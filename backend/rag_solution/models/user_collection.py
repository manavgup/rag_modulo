import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.rag_solution.file_management.database import Base


class UserCollection(Base):
    __tablename__ = "user_collection"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    collection_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("collections.id"), primary_key=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

    user = relationship("User", back_populates="collections")
    collection = relationship("Collection", back_populates="users")
