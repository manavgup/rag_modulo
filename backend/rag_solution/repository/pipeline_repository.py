"""Repository for managing Pipeline Configurations.

This module provides database operations for pipeline configurations while maintaining
strict type boundaries and clean separation of concerns.
"""

from typing import Any

from core.custom_exceptions import RepositoryError
from pydantic import UUID4
from sqlalchemy.orm import Session, joinedload

from rag_solution.core.exceptions import NotFoundError
from rag_solution.models.pipeline import PipelineConfig
from rag_solution.schemas.pipeline_schema import PipelineConfigInput, PipelineConfigOutput


class PipelineConfigRepository:
    """Repository for managing Pipeline Configurations.

    This class handles all database operations related to pipeline configurations,
    maintaining strict type boundaries between database models and schemas.

    Attributes:
        db (Session): SQLAlchemy database session
    """

    def __init__(self: Any, db: Session) -> None:
        """Initialize repository with database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def get_user_default(self, user_id: UUID4) -> PipelineConfigOutput | None:
        """Get the default pipeline for a user (non-collection specific).

        Args:
            user_id: UUID4 of the user

        Returns:
            Optional[PipelineConfigOutput]: The default pipeline configuration if found

        Raises:
            RepositoryError: If database operation fails
        """
        try:
            pipeline = (
                self.db.query(PipelineConfig)
                .filter(
                    PipelineConfig.user_id == user_id,
                    PipelineConfig.collection_id.is_(None),
                    PipelineConfig.is_default.is_(True),
                )
                .first()
            )
            return PipelineConfigOutput.from_db_model(pipeline) if pipeline else None
        except Exception as e:
            raise RepositoryError(f"Failed to get user default pipeline: {e!s}") from e

    def get_collection_default(self, collection_id: UUID4) -> PipelineConfigOutput | None:
        """Get the default pipeline for a collection.

        Args:
            collection_id: UUID of the collection

        Returns:
            Optional[PipelineConfigOutput]: The default pipeline configuration if found

        Raises:
            RepositoryError: If database operation fails
        """
        try:
            pipeline = (
                self.db.query(PipelineConfig)
                .filter(PipelineConfig.collection_id == collection_id, PipelineConfig.is_default.is_(True))
                .first()
            )
            return PipelineConfigOutput.from_db_model(pipeline) if pipeline else None
        except Exception as e:
            raise RepositoryError(f"Failed to get collection default pipeline: {e!s}") from e

    def create(self, config: PipelineConfigInput) -> PipelineConfigOutput:
        """Create a new pipeline configuration.

        Args:
            config: Pipeline configuration input schema

        Returns:
            PipelineConfigOutput: Created pipeline configuration

        Raises:
            RepositoryError: If creation fails
        """
        try:
            db_config = PipelineConfig(**config.model_dump())
            self.db.add(db_config)
            self.db.commit()
            self.db.refresh(db_config)
            return PipelineConfigOutput.from_db_model(db_config)
        except Exception as e:
            self.db.rollback()
            raise RepositoryError(f"Failed to create pipeline configuration: {e!s}") from e

    def get_by_id(self, pipeline_id: UUID4) -> PipelineConfigOutput:
        """Get pipeline configuration by ID.

        Args:
            pipeline_id: UUID of the pipeline configuration

        Returns:
            PipelineConfigOutput: Pipeline configuration

        Raises:
            NotFoundError: If pipeline not found
        """
        try:
            pipeline = self.db.query(PipelineConfig).filter(PipelineConfig.id == pipeline_id).first()
            if not pipeline:
                raise NotFoundError(resource_type="PipelineConfig", resource_id=str(pipeline_id))
            return PipelineConfigOutput.from_db_model(pipeline)
        except NotFoundError:
            raise
        except Exception as e:
            raise Exception(f"Failed to get pipeline by ID: {e!s}") from e

    def get_by_user(self, user_id: UUID4) -> list[PipelineConfigOutput]:
        """Get all pipelines for a user with optional filtering.

        Args:
            user_id: UUID4 of the user
            filters: Optional filter parameters

        Returns:
            List[PipelineConfigOutput]: List of matching pipeline configurations

        Raises:
            RepositoryError: If database operation fails
        """
        try:
            query = self.db.query(PipelineConfig).filter(PipelineConfig.user_id == user_id)

            # Always load provider relationship
            query = query.options(joinedload(PipelineConfig.provider))

            pipelines = query.all()
            return [PipelineConfigOutput.from_db_model(p) for p in pipelines]
        except Exception as e:
            raise RepositoryError(f"Failed to get pipelines for user: {e!s}") from e

    def update(self, id: UUID4, config: PipelineConfigInput) -> PipelineConfigOutput:
        """Update an existing pipeline configuration.

        Args:
            id: UUID of the pipeline to update
            config: Updated configuration input schema

        Returns:
            PipelineConfigOutput: Updated pipeline configuration

        Raises:
            NotFoundError: If pipeline not found
        """
        try:
            pipeline = self.db.query(PipelineConfig).filter(PipelineConfig.id == id).first()

            if not pipeline:
                raise NotFoundError(resource_type="PipelineConfig", resource_id=str(id))

            # If setting as default, clear other defaults first
            if config.is_default:
                if config.collection_id:
                    self.clear_collection_defaults(config.collection_id)
                else:
                    self.clear_user_defaults(config.user_id)

            # Update fields
            update_data = config.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(pipeline, field, value)

            self.db.commit()
            self.db.refresh(pipeline)
            return PipelineConfigOutput.from_db_model(pipeline)
        except NotFoundError:
            raise
        except Exception as e:
            self.db.rollback()
            raise Exception(f"Failed to update pipeline configuration: {e!s}") from e

    def delete(self, id: UUID4) -> bool:
        """Delete a pipeline configuration.

        Args:
            id: UUID of the pipeline to delete

        Returns:
            bool: True if deleted, False if not found

        Raises:
            RepositoryError: If deletion fails
        """
        try:
            result = self.db.query(PipelineConfig).filter(PipelineConfig.id == id).delete()
            self.db.commit()
            return result > 0
        except Exception as e:
            self.db.rollback()
            raise RepositoryError(f"Failed to delete pipeline configuration: {e!s}") from e

    def clear_collection_defaults(self, collection_id: UUID4) -> None:
        """Clear default flags for all pipelines in a collection.

        Args:
            collection_id: UUID of the collection

        Raises:
            RepositoryError: If operation fails
        """
        try:
            self.db.query(PipelineConfig).filter(
                PipelineConfig.collection_id == collection_id, PipelineConfig.is_default.is_(True)
            ).update({"is_default": False})
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise RepositoryError(f"Failed to clear collection defaults: {e!s}") from e

    def clear_user_defaults(self, user_id: UUID4) -> None:
        """Clear default flags for all user's non-collection pipelines.

        Args:
            user_id: UUID4 of the user

        Raises:
            RepositoryError: If operation fails
        """
        try:
            self.db.query(PipelineConfig).filter(
                PipelineConfig.user_id == user_id,
                PipelineConfig.collection_id.is_(None),
                PipelineConfig.is_default.is_(True),
            ).update({"is_default": False})
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise RepositoryError(f"Failed to clear user defaults: {e!s}") from e
