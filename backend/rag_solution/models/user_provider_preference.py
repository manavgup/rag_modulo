"""SQLAlchemy model for user provider preferences."""

from datetime import datetime
from typing import Optional
from uuid import UUID
from sqlalchemy import Column, Integer, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func

from rag_solution.file_management.database import Base
from rag_solution.models.provider_config import ProviderModelConfig

class UserProviderPreference(Base):
    """Model for storing user provider preferences."""
    
    __tablename__ = "user_provider_preferences"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    provider_config_id: Mapped[int] = mapped_column(
        ForeignKey("provider_model_configs.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    provider_config: Mapped[ProviderModelConfig] = relationship(
        "ProviderModelConfig",
        lazy="joined"
    )
    
    # Table constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'provider_config_id', name='uix_user_provider'),
    )
    
    def __repr__(self) -> str:
        """String representation of UserProviderPreference."""
        return (
            f"<UserProviderPreference("
            f"id={self.id}, "
            f"user_id={self.user_id}, "
            f"provider_config_id={self.provider_config_id})"
        )

    class Config:
        """Pydantic model configuration."""
        from_attributes = True
