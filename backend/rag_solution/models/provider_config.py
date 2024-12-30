"""SQLAlchemy models for provider configuration and registry."""

from typing import Optional
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import validates, relationship, Mapped, mapped_column
from sqlalchemy.sql import func

from rag_solution.file_management.database import Base
from rag_solution.models.llm_parameters import LLMParameters

class ProviderModelConfig(Base):
    """Model for storing LLM provider model configurations."""
    
    __tablename__ = "provider_model_configs"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Basic fields
    model_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )
    provider_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True
    )
    last_verified: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Foreign key to LLMParameters
    parameters_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('llm_parameters.id', ondelete='CASCADE'),
        nullable=False
    )
    
    # Relationship
    parameters: Mapped[LLMParameters] = relationship(
        "LLMParameters",
        lazy="joined"
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

    @validates('model_id')
    def validate_model_id(self, key: str, value: str) -> str:
        """Validate model_id is not empty and has proper format.
        
        Args:
            key: Field name being validated
            value: Value to validate
            
        Returns:
            Validated value
            
        Raises:
            ValueError: If value is empty or invalid
        """
        if not value or not value.strip():
            raise ValueError("model_id cannot be empty")
        return value.strip()

    @validates('provider_name')
    def validate_provider_name(self, key: str, value: str) -> str:
        """Validate provider_name is not empty and has proper format.
        
        Args:
            key: Field name being validated
            value: Value to validate
            
        Returns:
            Validated value
            
        Raises:
            ValueError: If value is empty or invalid
        """
        if not value or not value.strip():
            raise ValueError("provider_name cannot be empty")
        return value.strip().lower()

    def __repr__(self) -> str:
        """String representation of ProviderModelConfig."""
        return (
            f"<ProviderModelConfig("
            f"id={self.id}, "
            f"provider='{self.provider_name}', "
            f"model='{self.model_id}', "
            f"active={self.is_active})"
        )

    class Config:
        """Pydantic model configuration."""
        from_attributes = True
