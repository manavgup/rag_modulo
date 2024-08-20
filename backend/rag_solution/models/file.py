from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.rag_solution.file_management.database import Base


class File(Base):
    __tablename__ = "files"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    collection_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("collections.id"))
    filename: Mapped[str] = mapped_column(String, index=True)
    file_path: Mapped[str] = mapped_column(String, index=True)
    file_type: Mapped[str] = mapped_column(String)
    file_metadata: Mapped[JSON] = mapped_column(JSON, nullable=False, default=dict)  # Provide a default empty dict
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    user = relationship("User", back_populates="files")
    collection = relationship("Collection", back_populates="files")

    def __repr__(self):
        return f"File(id='{self.id}', filename='{self.filename}', file_type='{self.file_type}', collection_id='{self.collection_id}')"
