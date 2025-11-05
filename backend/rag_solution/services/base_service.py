"""Base service classes for configuration and common functionality.

This module provides base classes that services can inherit from to gain
access to common functionality like runtime configuration management.
"""

from typing import Any

from sqlalchemy.orm import Session

from core.config import Settings
from rag_solution.models.pipeline import PipelineConfig


class ConfigurableService:
    """Base service class with runtime configuration support.

    Provides hierarchical configuration resolution with precedence:
    1. Pipeline-level overrides (PipelineConfig.config_metadata)
    2. Global settings (.env via Settings class)
    3. Provided default value

    This enables runtime configuration changes without application restart
    for values stored in pipeline metadata, while falling back to Settings
    for infrastructure and default values.

    Example:
        >>> class MyService(ConfigurableService):
        ...     def process(self, pipeline: PipelineConfig):
        ...         batch_size = self.get_config("embedding_batch_size", pipeline, default=5)
        ...         # Uses: pipeline.config_metadata["embedding_batch_size"] if set,
        ...         # else self.settings.embedding_batch_size if exists,
        ...         # else default=5

    Attributes:
        db: SQLAlchemy database session
        settings: Application settings instance
    """

    def __init__(self, db: Session, settings: Settings):
        """Initialize configurable service.

        Args:
            db: SQLAlchemy database session
            settings: Application settings from .env
        """
        self.db = db
        self.settings = settings

    def get_config(
        self,
        key: str,
        pipeline: PipelineConfig | None = None,
        default: Any = None,
    ) -> Any:
        """Get configuration value with hierarchical precedence.

        Resolution order:
        1. Pipeline-level override (if pipeline provided and key exists in config_metadata)
        2. Global settings (if key exists as Settings attribute)
        3. Default value (if provided)

        Args:
            key: Configuration key to retrieve (e.g., 'max_new_tokens', 'temperature')
            pipeline: Optional pipeline config with metadata overrides
            default: Fallback value if key not found in pipeline or settings

        Returns:
            Configuration value from highest precedence source, or default

        Example:
            >>> # Pipeline has: config_metadata = {"temperature": 0.9}
            >>> # Settings has: temperature = 0.7
            >>> temp = self.get_config("temperature", pipeline, default=0.5)
            >>> # Returns: 0.9 (from pipeline metadata)

            >>> # Pipeline has no 'top_k' override
            >>> # Settings has: top_k = 50
            >>> top_k = self.get_config("top_k", pipeline, default=10)
            >>> # Returns: 50 (from settings)

            >>> # Neither pipeline nor settings has 'custom_value'
            >>> custom = self.get_config("custom_value", pipeline, default=100)
            >>> # Returns: 100 (default)
        """
        # Layer 1: Check pipeline metadata override
        if pipeline and pipeline.config_metadata and key in pipeline.config_metadata:
            return pipeline.config_metadata[key]

        # Layer 2: Check global settings
        if hasattr(self.settings, key):
            return getattr(self.settings, key)

        # Layer 3: Return default
        return default

    def set_pipeline_config(
        self,
        pipeline: PipelineConfig,
        key: str,
        value: Any,
    ) -> None:
        """Set a configuration value in pipeline metadata.

        This method updates the pipeline's config_metadata JSONB field.
        Changes are made to the in-memory object; caller is responsible
        for committing the database session.

        Args:
            pipeline: Pipeline configuration to update
            key: Configuration key to set
            value: Value to store

        Example:
            >>> pipeline = db.query(PipelineConfig).filter_by(id=pipeline_id).first()
            >>> service.set_pipeline_config(pipeline, "temperature", 0.9)
            >>> service.set_pipeline_config(pipeline, "enable_reranking", False)
            >>> db.commit()  # Persist changes
        """
        if pipeline.config_metadata is None:
            pipeline.config_metadata = {}

        pipeline.config_metadata[key] = value


class ServiceError(Exception):
    """Base exception for service-layer errors.

    Attributes:
        message: Human-readable error message
        details: Optional dictionary with additional error context
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        """Initialize service error.

        Args:
            message: Error message
            details: Optional dictionary with error context
        """
        self.message = message
        self.details = details or {}
        super().__init__(self.message)
