"""SQLAlchemy models for provider configuration and registry."""

from typing import Optional
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float, select
from sqlalchemy.orm import validates, relationship, Mapped, mapped_column, object_session
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
    
    # Provider credentials
    api_key: Mapped[str] = mapped_column(
        String(1024),
        nullable=False
    )
    api_url: Mapped[Optional[str]] = mapped_column(
        String(1024),
        nullable=True
    )
    project_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    org_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    
    # Model settings
    default_model_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    embedding_model: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    
    # Runtime settings
    timeout: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=30
    )
    max_retries: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3
    )
    batch_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10
    )
    retry_delay: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0
    )
    concurrency_limit: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10
    )
    stream: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )
    rate_limit: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10
    )
    
    # Status and defaults
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
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

    @validates('model_id', 'provider_name', 'api_key', 'default_model_id')
    def validate_required_string(self, key: str, value: str) -> str:
        """Validate required string fields are not empty.
        
        Args:
            key: Field name being validated
            value: Value to validate
            
        Returns:
            Validated value
            
        Raises:
            ValueError: If value is empty
        """
        if not value or not value.strip():
            raise ValueError(f"{key} cannot be empty")
        value = value.strip()
        return value.lower() if key == 'provider_name' else value

    @validates('timeout', 'max_retries', 'batch_size', 'concurrency_limit', 'rate_limit')
    def validate_positive_int(self, key: str, value: int) -> int:
        """Validate integer fields are positive."""
        if value <= 0:
            raise ValueError(f"{key} must be positive")
        return value

    @validates('retry_delay')
    def validate_positive_float(self, key: str, value: float) -> float:
        """Validate float fields are positive."""
        if value < 0:
            raise ValueError(f"{key} must be non-negative")
        return value

    @validates('is_default')
    def validate_default(self, key: str, value: bool) -> bool:
        """Validate is_default field.
        
        Ensures:
        1. Value is not empty
        2. Only one default provider exists
        
        Args:
            key: Field name being validated
            value: Value to validate
            
        Returns:
            bool: Validated value
            
        Raises:
            ValueError: If value is invalid
        """
        # Ensure value is not None
        if value is None:
            raise ValueError("is_default cannot be None")
            
        # Ensure only one default exists
        if value and hasattr(self, 'id'):  # Skip during creation
            session = object_session(self)
            if not session:
                # Can't check for other defaults without session
                return value
                
            stmt = select(self.__class__).where(
                self.__class__.is_default == True,
                self.__class__.id != self.id
            )
            current_default = session.execute(stmt).scalar_one_or_none()
            if current_default:
                current_default.is_default = False
                
        return value

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
