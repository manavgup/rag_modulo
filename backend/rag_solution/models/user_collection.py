from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from rag_solution.file_management.database import Base

if TYPE_CHECKING:

    from rag_solution.models.collection import Collection
    from rag_solution.models.user import User


class UserCollection(Base):
    """Association model representing the many-to-many relationship between users and collections.

    This model uses composite primary keys (user_id, collection_id) and maintains the timestamp
    when a user joined a collection. It implements eager loading through selectin strategy
    for both user and collection relationships to optimize query performance.

    Attributes:
        user_id (UUID): Foreign key to users table, part of composite primary key
        collection_id (UUID): Foreign key to collections table, part of composite primary key
        joined_at (datetime): Timestamp when the user joined the collection
        user (User): Relationship to User model, eagerly loaded
        collection (Collection): Relationship to Collection model, eagerly loaded
    """

    __tablename__ = "user_collection"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    collection_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("collections.id"), primary_key=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

    user: Mapped[User] = relationship("User", back_populates="collections", lazy="selectin")
    collection: Mapped[Collection] = relationship("Collection", back_populates="users", lazy="selectin")
