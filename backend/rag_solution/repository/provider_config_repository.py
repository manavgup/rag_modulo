"""Repository for managing provider configurations in the database."""

from typing import List, Optional, cast
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, update, desc, func

from core.logging_utils import get_logger
from core.custom_exceptions import ProviderConfigError
from rag_solution.models.provider_config import ProviderModelConfig
from rag_solution.schemas.provider_config_schema import (
    ProviderConfig,
    ProviderInDB,
    ProviderRuntimeSettings,
    ProviderUpdate,
    ProviderRegistry
)

logger = get_logger("repository.provider_config")

class ProviderConfigRepository:
    """Repository for managing provider configurations in the database."""

    def __init__(self, session: Session) -> None:
        """Initialize repository with database session.
        
        Args:
            session: SQLAlchemy database session
        """
        self.session = session
        self.logger = get_logger(__name__)

    def create(self, config: ProviderConfig) -> ProviderConfig:
        """Create new provider configuration.
        
        Args:
            config: Configuration to create
            
        Returns:
            Created configuration
            
        Raises:
            ProviderConfigError: If creation fails
        """
        try:
            # Convert config to dict and handle runtime settings
            config_dict = config.model_dump()
            runtime_settings = config_dict.pop('runtime', {})
            config_dict.update(runtime_settings)  # Flatten runtime settings into main config
            
            db_config = ProviderModelConfig(**config_dict)
            self.session.add(db_config)
            self.session.commit()
            self.session.refresh(db_config)
            
            created = self._to_response(db_config)
            if created is None:
                raise ValueError("Failed to create provider configuration")
                
            self.logger.info(
                f"Created provider config: {created.provider_name}/{created.model_id}"
            )
            return created
        except Exception as e:
            self.logger.error(f"Error creating provider config: {str(e)}")
            self.session.rollback()
            raise ProviderConfigError(
                provider=config.provider_name,
                model_id=config.model_id,
                error_type="creation_error",
                message=f"Failed to create provider configuration: {str(e)}"
            )

    def get(self, config_id: int) -> Optional[ProviderConfig]:
        """Get provider configuration by ID.
        
        Args:
            config_id: ID of configuration to retrieve
            
        Returns:
            Configuration if found, None otherwise
            
        Raises:
            ProviderConfigError: If database error occurs
        """
        try:
            stmt = (
                select(ProviderModelConfig)
                .where(ProviderModelConfig.id == config_id)
            )
            result = self.session.execute(stmt).scalar_one_or_none()
            return self._to_response(result) if result else None
        except Exception as e:
            self.logger.error(f"Error getting provider config {config_id}: {str(e)}")
            raise ProviderConfigError(
                provider="unknown",
                model_id=str(config_id),
                error_type="retrieval_error",
                message=f"Failed to retrieve provider configuration: {str(e)}"
            )

    def get_by_provider_and_model(
        self,
        provider: str,
        model_id: str
    ) -> Optional[ProviderConfig]:
        """Get provider configuration by provider name and model ID.
        
        Args:
            provider: Provider name
            model_id: Model ID
            
        Returns:
            Configuration if found, None otherwise
            
        Raises:
            ProviderConfigError: If database error occurs
        """
        try:
            stmt = (
                select(ProviderModelConfig)
                .where(
                    ProviderModelConfig.provider_name == provider.lower(),
                    ProviderModelConfig.model_id == model_id
                )
            )
            result = self.session.execute(stmt).scalar_one_or_none()
            return self._to_response(result) if result else None
        except Exception as e:
            self.logger.error(
                f"Error getting provider config for {provider}/{model_id}: {str(e)}"
            )
            raise ProviderConfigError(
                provider=provider,
                model_id=model_id,
                error_type="retrieval_error",
                message=f"Failed to retrieve provider configuration: {str(e)}"
            )

    def list(
        self,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = False
    ) -> ProviderRegistry:
        """List provider configurations with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            active_only: If True, only return active configurations
            
        Returns:
            Registry response with configurations and counts
            
        Raises:
            ProviderConfigError: If database error occurs
        """
        try:
            # Base query
            query = select(ProviderModelConfig)
            
            # Add active filter if requested
            if active_only:
                query = query.where(ProviderModelConfig.is_active == True)
            
            # Get total counts
            count_stmt = select(func.count()).select_from(ProviderModelConfig)
            active_count_stmt = select(func.count()).select_from(ProviderModelConfig).where(
                ProviderModelConfig.is_active == True
            )
            
            total = self.session.execute(count_stmt).scalar_one()
            active = self.session.execute(active_count_stmt).scalar_one()
            
            # Get paginated results
            results = (
                self.session.execute(
                    query.order_by(desc(ProviderModelConfig.updated_at))
                    .offset(skip)
                    .limit(limit)
                )
                .scalars()
                .all()
            )
            
            # Convert results to response schemas
            configs = []
            for result in results:
                config = self._to_response(result)
                if config:
                    configs.append(config)
            
            # Create registry response
            return ProviderRegistry(
                total_providers=total,
                active_providers=active,
                providers=configs
            )
        except Exception as e:
            self.logger.error(f"Error listing provider configs: {str(e)}")
            raise ProviderConfigError(
                provider="all",
                model_id="all",
                error_type="retrieval_error",
                message=f"Failed to list provider configurations: {str(e)}"
            )

    def update(
        self,
        config_id: int,
        config: ProviderUpdate
    ) -> Optional[ProviderConfig]:
        """Update provider configuration.
        
        Args:
            config_id: ID of configuration to update
            config: Updated configuration values
            
        Returns:
            Updated configuration if found, None otherwise
            
        Raises:
            ProviderConfigError: If update fails
        """
        try:
            # Get existing config
            stmt = select(ProviderModelConfig).where(ProviderModelConfig.id == config_id)
            db_config = self.session.execute(stmt).scalar_one_or_none()
            
            if not db_config:
                return None

            # Update config
            update_data = config.model_dump(exclude_unset=True)
            # Handle runtime settings if present
            if 'runtime' in update_data:
                runtime = update_data.pop('runtime')
                update_data.update(runtime)
                
            for key, value in update_data.items():
                setattr(db_config, key, value)

            # Update timestamp
            db_config.updated_at = datetime.utcnow()

            self.session.commit()
            self.session.refresh(db_config)
            
            updated = self._to_response(db_config)
            if updated is not None:
                self.logger.info(
                    f"Updated provider config: {updated.provider_name}/{updated.model_id}"
                )
            return updated
        except Exception as e:
            self.logger.error(f"Error updating provider config {config_id}: {str(e)}")
            self.session.rollback()
            raise ProviderConfigError(
                provider="unknown",
                model_id=str(config_id),
                error_type="update_error",
                message=f"Failed to update provider configuration: {str(e)}"
            )

    def delete(self, config_id: int) -> bool:
        """Delete provider configuration.
        
        Args:
            config_id: ID of configuration to delete
            
        Returns:
            True if deleted successfully, False if not found
            
        Raises:
            ProviderConfigError: If deletion fails
        """
        try:
            stmt = select(ProviderModelConfig).where(ProviderModelConfig.id == config_id)
            db_config = self.session.execute(stmt).scalar_one_or_none()
            
            if not db_config:
                return False

            provider = db_config.provider_name
            model = db_config.model_id
            
            self.session.delete(db_config)
            self.session.commit()
            
            self.logger.info(f"Deleted provider config: {provider}/{model}")
            return True
        except Exception as e:
            self.logger.error(f"Error deleting provider config {config_id}: {str(e)}")
            self.session.rollback()
            raise ProviderConfigError(
                provider="unknown",
                model_id=str(config_id),
                error_type="deletion_error",
                message=f"Failed to delete provider configuration: {str(e)}"
            )

    def update_verification(self, config_id: int) -> Optional[ProviderConfig]:
        """Update last_verified timestamp for a provider configuration.
        
        Args:
            config_id: ID of configuration to update
            
        Returns:
            Updated configuration if found, None otherwise
            
        Raises:
            ProviderConfigError: If update fails
        """
        try:
            stmt = select(ProviderModelConfig).where(ProviderModelConfig.id == config_id)
            db_config = self.session.execute(stmt).scalar_one_or_none()
            
            if not db_config:
                return None

            db_config.last_verified = datetime.utcnow()
            db_config.updated_at = datetime.utcnow()

            self.session.commit()
            self.session.refresh(db_config)
            
            updated = self._to_response(db_config)
            if updated is not None:
                self.logger.info(
                    f"Updated verification for: {updated.provider_name}/{updated.model_id}"
                )
            return updated
        except Exception as e:
            self.logger.error(
                f"Error updating verification for config {config_id}: {str(e)}"
            )
            self.session.rollback()
            raise ProviderConfigError(
                provider="unknown",
                model_id=str(config_id),
                error_type="update_error",
                message=f"Failed to update verification timestamp: {str(e)}"
            )

    @staticmethod
    def _to_response(
        config: Optional[ProviderModelConfig]
    ) -> Optional[ProviderConfig]:
        """Convert database model to response schema.
        
        Args:
            config: Database model instance or None
            
        Returns:
            Response schema instance if config is not None, otherwise None
        """
        if config is None:
            return None
            
        # Extract runtime settings
        runtime_fields = {
            'timeout', 'max_retries', 'batch_size', 'retry_delay',
            'concurrency_limit', 'stream', 'rate_limit'
        }
        config_dict = config.__dict__
        runtime_settings = {
            k: config_dict[k] for k in runtime_fields 
            if k in config_dict
        }
        
        # Remove runtime fields from main config
        for field in runtime_fields:
            config_dict.pop(field, None)
            
        # Add runtime config
        config_dict['runtime'] = ProviderRuntimeSettings(**runtime_settings)
        
        return ProviderConfig.model_validate(config_dict)
