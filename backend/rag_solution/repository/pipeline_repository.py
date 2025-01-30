"""Repository for managing Pipeline Configurations."""

from sqlalchemy.orm import Session, joinedload
from typing import Optional, List
from uuid import UUID

from rag_solution.models.collection import Collection
from rag_solution.models.pipeline import PipelineConfig
from rag_solution.models.user_collection import UserCollection
from rag_solution.schemas.pipeline_schema import PipelineConfigInput, PipelineConfigOutput


class PipelineConfigRepository:
    """Repository for managing Pipeline Configurations."""

    def __init__(self, db: Session):
        self.db = db
    
    def get_collection_default(self, collection_id: UUID) -> Optional[PipelineConfigOutput]:
        """Get the default pipeline for a collection."""
        pipeline = self.db.query(PipelineConfig).filter(
            PipelineConfig.collection_id == collection_id,
            PipelineConfig.is_default.is_(True)
        ).first()
        return PipelineConfigOutput.from_db_model(pipeline) if pipeline else None

    def _get_db_model(self, pipeline_id: UUID) -> Optional[PipelineConfig]:
        """Get raw database model by ID."""
        return self.db.query(PipelineConfig).filter(PipelineConfig.id == pipeline_id).first()

    def create(self, config: dict) -> PipelineConfigOutput:
        """
        Create a new pipeline configuration.
        
        Args:
            config: Dictionary containing pipeline configuration
            
        Returns:
            PipelineConfigOutput containing created pipeline
        """
        db_config = PipelineConfig(**config)
        self.db.add(db_config)
        self.db.commit()
        self.db.refresh(db_config)
        return PipelineConfigOutput.from_db_model(db_config)

    def get_by_id(self, pipeline_id: UUID) -> Optional[PipelineConfigOutput]:
        """Get pipeline configuration by ID converted to schema."""
        pipeline = self._get_db_model(pipeline_id)
        if not pipeline:
            return None
        return PipelineConfigOutput.from_db_model(pipeline)

    def get_by_user(self, user_id: UUID, include_system: bool = True) -> List[PipelineConfigOutput]:
        """
        Get all pipelines for a user through their collection access.
        
        Args:
            user_id: User ID to get pipelines for
            include_system: Whether to include system-wide pipelines (collection_id is null)
            
        Returns:
            List of pipeline configurations the user has access to
        """
        # Start with base query
        base_query = self.db.query(PipelineConfig)
        
        if include_system:
            # Get both collection-specific and system-wide pipelines
            query = base_query.filter(
                (PipelineConfig.collection_id.is_(None)) |  # System-wide pipelines
                (PipelineConfig.collection_id.in_(  # User's collection-specific pipelines
                    self.db.query(UserCollection.collection_id)
                    .filter(UserCollection.user_id == user_id)
                ))
            )
        else:
            # Only get collection-specific pipelines
            query = base_query.filter(
                PipelineConfig.collection_id.in_(
                    self.db.query(UserCollection.collection_id)
                    .filter(UserCollection.user_id == user_id)
                )
            )
        
        # Load provider relationship
        query = query.options(joinedload(PipelineConfig.provider))
        
        return [PipelineConfigOutput.from_db_model(p) for p in query.all()]

    def get_by_collection_id(self, collection_id: UUID) -> List[PipelineConfigOutput]:
        """Get all pipelines for a collection."""
        pipelines = self.db.query(PipelineConfig).filter(
            PipelineConfig.collection_id == collection_id
        ).all()
        return [PipelineConfigOutput.from_db_model(p) for p in pipelines]

    def update(self, id: UUID, config: PipelineConfigInput) -> Optional[PipelineConfigOutput]:
        db_config = self._get_db_model(id)
        if not db_config:
            return None
        
        # If setting as default, clear other defaults first
        if config.is_default and db_config.collection_id:
            self.clear_collection_defaults(db_config.collection_id)
        
        # Update fields
        for field, value in config.model_dump(exclude_unset=True).items():
            setattr(db_config, field, value)
        
        self.db.commit()
        self.db.refresh(db_config)
        return PipelineConfigOutput.from_db_model(db_config)

    def delete(self, id: UUID) -> bool:
        """Delete pipeline configuration by ID."""
        db_config = self._get_db_model(id)
        if not db_config:
            return False

        self.db.delete(db_config)
        self.db.commit()
        return True

    def clear_collection_defaults(self, collection_id: UUID) -> None:
        """Clear any existing default pipeline for a collection."""
        self.db.query(PipelineConfig).filter(
            PipelineConfig.collection_id == collection_id,
            PipelineConfig.is_default.is_(True)
        ).update({"is_default": False})
        self.db.commit()

    def clear_default(self) -> None:
        """Clear the default flag from all pipelines."""
        self.db.query(PipelineConfig).filter(
            PipelineConfig.is_default.is_(True)
        ).update({"is_default": False})
        self.db.commit()
