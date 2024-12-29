"""SQLAlchemy model for LLM parameters."""

from typing import Optional
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import validates, Mapped, mapped_column
from sqlalchemy.sql import func
from rag_solution.file_management.database import Base

class LLMParameters(Base):
    """Model for storing LLM generation parameters."""
    
    __tablename__ = "llm_parameters"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Basic fields
    name: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    # LLM parameters
    max_new_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100
    )
    min_new_tokens: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    temperature: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.7
    )
    top_k: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=50
    )
    top_p: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0
    )
    random_seed: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    
    # Status flags
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True
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

    @validates('max_new_tokens')
    def validate_max_tokens(self, key: str, value: int) -> int:
        """Validate max_new_tokens is within acceptable range.
        
        Args:
            key: Field name being validated
            value: Value to validate
            
        Returns:
            Validated value
            
        Raises:
            ValueError: If value is outside acceptable range
        """
        if not 1 <= value <= 2048:
            raise ValueError("max_new_tokens must be between 1 and 2048")
        return value

    @validates('min_new_tokens')
    def validate_min_tokens(self, key: str, value: Optional[int]) -> Optional[int]:
        """Validate min_new_tokens is within acceptable range and less than max_new_tokens.
        
        Args:
            key: Field name being validated
            value: Value to validate
            
        Returns:
            Validated value
            
        Raises:
            ValueError: If value is outside acceptable range or greater than max_new_tokens
        """
        if value is not None:
            if not 1 <= value <= 2048:
                raise ValueError("min_new_tokens must be between 1 and 2048")
            if hasattr(self, 'max_new_tokens') and value > self.max_new_tokens:
                raise ValueError("min_new_tokens must be less than or equal to max_new_tokens")
        return value

    @validates('temperature')
    def validate_temperature(self, key: str, value: float) -> float:
        """Validate temperature is within acceptable range.
        
        Args:
            key: Field name being validated
            value: Value to validate
            
        Returns:
            Validated value
            
        Raises:
            ValueError: If value is outside acceptable range
        """
        if not 0.0 <= value <= 2.0:
            raise ValueError("temperature must be between 0.0 and 2.0")
        return value

    @validates('top_k')
    def validate_top_k(self, key: str, value: int) -> int:
        """Validate top_k is within acceptable range.
        
        Args:
            key: Field name being validated
            value: Value to validate
            
        Returns:
            Validated value
            
        Raises:
            ValueError: If value is outside acceptable range
        """
        if not 1 <= value <= 100:
            raise ValueError("top_k must be between 1 and 100")
        return value

    @validates('top_p')
    def validate_top_p(self, key: str, value: float) -> float:
        """Validate top_p is within acceptable range.
        
        Args:
            key: Field name being validated
            value: Value to validate
            
        Returns:
            Validated value
            
        Raises:
            ValueError: If value is outside acceptable range
        """
        if not 0.0 <= value <= 1.0:
            raise ValueError("top_p must be between 0.0 and 1.0")
        return value

    def __repr__(self) -> str:
        """String representation of LLMParameters."""
        return (
            f"<LLMParameters("
            f"id={self.id}, "
            f"name='{self.name}', "
            f"is_default={self.is_default}, "
            f"updated_at='{self.updated_at}')"
        )
