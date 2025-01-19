"""Repository module for LLM Provider management with strong typing and Pydantic 2.0 validation."""

from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from pydantic import SecretStr

from rag_solution.models.llm_provider import LLMProvider, LLMProviderModel
from rag_solution.schemas.llm_provider_schema import (
    LLMProviderInput,
    LLMProviderOutput,
    LLMProviderModelInput,
    LLMProviderModelOutput,
    ModelType
)
from core.logging_utils import get_logger

logger = get_logger("repository.llm_provider")

class LLMProviderRepository:
    """Repository for managing LLM Providers and their Models.
    
    This repository handles CRUD operations for LLM providers and their associated models.
    It ensures proper data validation and type safety using Pydantic models.
    
    Attributes:
        db (Session): SQLAlchemy database session for database operations
        provider_adapter (TypeAdapter): Pydantic type adapter for LLMProvider validation
        model_adapter (TypeAdapter): Pydantic type adapter for LLMProviderModel validation
    """
    
    def __init__(self, db: Session) -> None:
        """Initialize repository with database session and type adapters.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def _convert_provider_data(self, provider_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Pydantic types to database-compatible types.
        
        Args:
            provider_data: Dictionary of provider data
            
        Returns:
            Dictionary with converted types
        """
        converted = provider_data.copy()
        
        # Convert SecretStr to string if present
        api_key = converted.get('api_key')
        if isinstance(api_key, SecretStr):
            converted['api_key'] = api_key.get_secret_value()
        
        return converted

    # -------------------------------
    # PROVIDER METHODS
    # -------------------------------
    def get_default_provider(self) -> Optional[LLMProvider]:
        """Get the system default provider."""
        return (
            self.db.query(LLMProvider)
            .filter(LLMProvider.is_active == True)
            .filter(LLMProvider.is_default == True)
            .first()
        )

    def get_user_preferred_provider(self, user_id: UUID) -> Optional[LLMProvider]:
        """Get user's preferred provider if set."""
        # This requires adding a user_providers table/relationship
        # For now, return None to fall back to default
        return None

    def create_provider(self, provider_input: LLMProviderInput) -> LLMProviderOutput:
        """Create a new LLM provider with a generated UUID.
        
        Args:
            provider_input: Validated provider input data
            
        Returns:
            Created provider instance with generated ID
            
        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            provider_data = provider_input.model_dump()
            
            # Convert Pydantic types to database types
            provider_data = self._convert_provider_data(provider_data)
            
            # Create provider with SQLAlchemy model
            provider = LLMProvider(**provider_data)
            self.db.add(provider)
            self.db.commit()
            self.db.refresh(provider)
            
            # Convert to Pydantic model after SQLAlchemy has set all fields
            return LLMProviderOutput.model_validate(provider, from_attributes=True, context={"session": self.db})
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e

    def get_all_providers(self, is_active: Optional[bool] = None) -> List[LLMProviderOutput]:
        """Retrieve all providers, optionally filtering by active status.
        
        Args:
            is_active: Optional filter for active/inactive providers
            
        Returns:
            List of provider instances matching the filter
        """
        query = self.db.query(LLMProvider)
        if is_active is not None:
            query = query.filter(LLMProvider.is_active == is_active)
        providers = query.all()
        return [LLMProviderOutput.model_validate(p, from_attributes=True) for p in providers]

    def get_provider_by_id(self, provider_id: UUID) -> Optional[LLMProviderOutput]:
        """Retrieve a specific provider by ID.
        
        Args:
            provider_id: UUID of the provider to retrieve
            
        Returns:
            Provider instance if found, None otherwise
        """
        provider = self.db.query(LLMProvider).filter(LLMProvider.id == provider_id).first()
        return LLMProviderOutput.model_validate(provider, from_attributes=True) if provider else None

    def update_provider(self, provider_id: UUID, updates: Dict[str, Any]) -> Optional[LLMProviderOutput]:
        """Update provider details.
        
        Args:
            provider_id: UUID of the provider to update
            updates: Dictionary of fields to update
            
        Returns:
            Updated provider instance if found, None otherwise
            
        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            provider = self.db.query(LLMProvider).filter(LLMProvider.id == provider_id).first()
            if not provider:
                return None
            
            # Convert Pydantic types to database types
            updates = self._convert_provider_data(updates)
            
            for key, value in updates.items():
                setattr(provider, key, value)
            
            self.db.commit()
            self.db.refresh(provider)
            return LLMProviderOutput.model_validate(provider, from_attributes=True)
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e

    def delete_provider(self, provider_id: UUID) -> bool:
        """Soft delete a provider by marking it inactive.
        
        Args:
            provider_id: UUID of the provider to delete
            
        Returns:
            True if provider was deleted, False if not found
            
        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            provider = self.db.query(LLMProvider).filter(LLMProvider.id == provider_id).first()
            if not provider:
                return False
            
            provider.is_active = False
            self.db.commit()
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e

    # -------------------------------
    # PROVIDER MODEL METHODS
    # -------------------------------

    def create_provider_model(self, model_input: LLMProviderModelInput) -> LLMProviderModelOutput:
        """Create a new model configuration for a provider with a generated UUID.
        
        Args:
            model_input: Validated model input data
            
        Returns:
            Created model instance with generated ID
            
        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            model_data = model_input.model_dump()
            model_data['id'] = uuid4()
            model = LLMProviderModel(**model_data)
            self.db.add(model)
            self.db.commit()
            self.db.refresh(model)
            return LLMProviderModelOutput.model_validate(model, from_attributes=True)
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e

    def get_models_by_provider(self, provider_id: UUID) -> List[LLMProviderModelOutput]:
        """Retrieve all models associated with a specific provider.
        
        Args:
            provider_id: UUID of the provider to get models for
            
        Returns:
            List of model instances for the provider
        """
        models = (
            self.db.query(LLMProviderModel)
            .filter(LLMProviderModel.provider_id == provider_id)
            .all()
        )
        return [LLMProviderModelOutput.model_validate(m, from_attributes=True) for m in models]

    def get_models_by_type(self, model_type: ModelType) -> List[LLMProviderModelOutput]:
        """Retrieve all models of a specific type.
        
        Args:
            model_type: Type of models to retrieve (e.g., embedding, generation)
            
        Returns:
            List of model instances matching the type
        """
        models = (
            self.db.query(LLMProviderModel)
            .filter(LLMProviderModel.model_type == model_type)
            .all()
        )
        return [LLMProviderModelOutput.model_validate(m, from_attributes=True) for m in models]

    def get_model_by_id(self, model_id: UUID) -> Optional[LLMProviderModelOutput]:
        """Retrieve a specific model by ID.
        
        Args:
            model_id: UUID of the model to retrieve
            
        Returns:
            Model instance if found, None otherwise
        """
        model = (
            self.db.query(LLMProviderModel)
            .filter(LLMProviderModel.id == model_id)
            .first()
        )
        return LLMProviderModelOutput.model_validate(model, from_attributes=True) if model else None

    def update_model(self, model_id: UUID, updates: Dict[str, Any]) -> Optional[LLMProviderModelOutput]:
        """Update model configuration details.
        
        Args:
            model_id: UUID of the model to update
            updates: Dictionary of fields to update
            
        Returns:
            Updated model instance if found, None otherwise
            
        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            model = self.db.query(LLMProviderModel).filter(LLMProviderModel.id == model_id).first()
            if not model:
                return None
            
            for key, value in updates.items():
                setattr(model, key, value)
            
            self.db.commit()
            self.db.refresh(model)
            return LLMProviderModelOutput.model_validate(model, from_attributes=True)
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e

    def delete_model(self, model_id: UUID) -> bool:
        """Soft delete a model by marking it inactive.
        
        Args:
            model_id: UUID of the model to delete
            
        Returns:
            True if model was deleted, False if not found
            
        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            model = self.db.query(LLMProviderModel).filter(LLMProviderModel.id == model_id).first()
            if not model:
                return False
            
            model.is_active = False
            self.db.commit()
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e

    # -------------------------------
    # PROVIDER WITH MODELS
    # -------------------------------

    def get_provider_with_models(self, provider_id: UUID) -> Optional[LLMProviderOutput]:
        """Retrieve a provider along with its models.
        
        Args:
            provider_id: UUID of the provider to retrieve with models
            
        Returns:
            Provider instance with loaded models if found, None otherwise
        """
        provider = (
            self.db.query(LLMProvider)
            .filter(LLMProvider.id == provider_id)
            .join(LLMProvider.models)
            .first()
        )
        return LLMProviderOutput.model_validate(provider, from_attributes=True) if provider else None
