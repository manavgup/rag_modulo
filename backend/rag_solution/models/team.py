from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.identity_service import IdentityService
from rag_solution.file_management.database import Base

if TYPE_CHECKING:
    from rag_solution.models.agent import Agent
    from rag_solution.models.user_team import UserTeam


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=IdentityService.generate_id)
    name: Mapped[str] = mapped_column(String, index=True, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    users: Mapped[list[UserTeam]] = relationship("UserTeam", back_populates="team")
    agents: Mapped[list[Agent]] = relationship("Agent", back_populates="team")

    def __repr__(self) -> str:
        return f"Team(id='{self.id}', name='{self.name}')"
