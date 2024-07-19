from sqlalchemy import ForeignKey, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from backend.rag_solution.models.collection import Collection
from ..file_management.database import Base

class File(Base):
    __tablename__ = "files"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    collection_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("collections.id"))
    filename: Mapped[str] = mapped_column(String, index=True)
    filepath: Mapped[str] = mapped_column(String, index=True)
    file_type: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    collection: Mapped["Collection"] = relationship(back_populates="files")

    def __repr__(self):
        return f"File(id='{self.id}',\
                filename='{self.filename}',\
                    file_type='{self.file_type}',\
                    collection_id='{self.collection_id}')"
