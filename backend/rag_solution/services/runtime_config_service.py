"""Service for managing runtime configurations."""

import logging
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from pydantic import BaseModel

from rag_solution.models.provider_config import ProviderModelConfig
from rag_solution.schemas.provider_config_schema import ProviderOutput
from rag_solution.models.user_provider_preference import UserProviderPreference
from rag_solution.models.llm_parameters import LLMParameters
from rag_solution.models.prompt_template import PromptTemplate
from core.custom_exceptions import ConfigurationError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RuntimeServiceConfig(BaseModel):
    """Container for service runtime configuration.
    
    This class represents the complete runtime configuration needed for the service,
    including provider settings, LLM parameters, and prompt templates.
    
    This is distinct from the provider-level RuntimeConfig which handles
    provider-specific settings like timeouts and retries.
    """
    
    provider_config: ProviderOutput
    llm_parameters: LLMParameters
    prompt_template: PromptTemplate
    
    model_config = {
        "arbitrary_types_allowed": True,
        "from_attributes": True
    }

class RuntimeConfigService:
    """Service for managing runtime configurations."""
    
    def __init__(self, db: Session):
        """Initialize runtime config service.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def get_runtime_config(
        self,
        user_id: Optional[UUID] = None
    ) -> RuntimeServiceConfig:
        """Get runtime configuration based on context.
        
        Selection hierarchy:
        1. User preference if user_id provided
        2. System default provider
        3. First active provider
        
        Args:
            user_id: Optional user ID for preferences
            
        Returns:
            RuntimeServiceConfig: Current runtime configuration
            
        Raises:
            ConfigurationError: If no valid configuration found
        """
        try:
            # Get provider config using hierarchy
            provider_config = self._get_provider_config(user_id)
            
            # Get associated configurations
            llm_params = self._get_llm_parameters(provider_config.parameters_id)
            prompt_template = self._get_prompt_template(provider_config.provider_name)
            
            return RuntimeServiceConfig(
                provider_config=provider_config,
                llm_parameters=llm_params,
                prompt_template=prompt_template
            )
            
        except Exception as e:
            logger.error(f"Error getting runtime config: {e}")
            raise ConfigurationError(f"Failed to get runtime configuration: {str(e)}")
    
    def _get_provider_config(
        self,
        user_id: Optional[UUID] = None
    ) -> ProviderOutput:
        """Get appropriate provider configuration.
        
        Args:
            user_id: Optional user ID to check preferences
            
        Returns:
            ProviderOutput: Selected provider configuration
            
        Raises:
            ConfigurationError: If no valid provider found
        """
        if user_id:
            # Check user preference
            stmt = select(UserProviderPreference)\
                .join(ProviderModelConfig)\
                .filter(
                    UserProviderPreference.user_id == user_id,
                    ProviderModelConfig.is_active == True
                )
            result = self.db.execute(stmt)
            preference = result.scalar_one_or_none()
            if preference:
                return ProviderOutput.model_validate(preference.provider_config)
        
        # Check system default
        stmt = select(ProviderModelConfig).filter(
            ProviderModelConfig.is_default == True,
            ProviderModelConfig.is_active == True
        )
        result = self.db.execute(stmt)
        default_provider = result.scalar_one_or_none()
        if default_provider:
            return ProviderOutput.model_validate(default_provider)
            
        # Fall back to first active provider
        stmt = select(ProviderModelConfig).filter(
            ProviderModelConfig.is_active == True
        )
        result = self.db.execute(stmt)
        active_provider = result.scalar_one_or_none()
        if active_provider:
            return ProviderOutput.model_validate(active_provider)
            
        raise ConfigurationError("No valid provider configuration found")
    
    def _get_llm_parameters(
        self,
        parameters_id: int
    ) -> LLMParameters:
        """Get LLM parameters by ID.
        
        Args:
            parameters_id: ID of parameters to fetch
            
        Returns:
            LLMParameters: Parameters configuration
            
        Raises:
            ConfigurationError: If parameters not found
        """
        stmt = select(LLMParameters).filter(LLMParameters.id == parameters_id)
        result = self.db.execute(stmt)
        params = result.scalar_one_or_none()
        if not params:
            raise ConfigurationError(f"LLM parameters not found: {parameters_id}")
        return params
    
    def _get_prompt_template(
        self,
        provider_name: str
    ) -> PromptTemplate:
        """Get prompt template for provider.
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            PromptTemplate: Provider's prompt template
            
        Raises:
            ConfigurationError: If no template found
        """
        # Try to get default template for provider
        stmt = select(PromptTemplate).filter(
            PromptTemplate.provider == provider_name,
            PromptTemplate.is_default == True
        )
        result = self.db.execute(stmt)
        template = result.scalar_one_or_none()
        
        # Fall back to any template for provider
        if not template:
            stmt = select(PromptTemplate).filter(
                PromptTemplate.provider == provider_name
            )
            result = self.db.execute(stmt)
            template = result.scalar_one_or_none()
            
        if not template:
            raise ConfigurationError(
                f"No prompt template found for provider: {provider_name}"
            )
            
        return template
    
    def set_user_provider_preference(
        self,
        user_id: UUID,
        provider_config_id: int
    ) -> UserProviderPreference:
        """Set user's preferred provider.
        
        Args:
            user_id: User ID
            provider_config_id: Provider config ID
            
        Returns:
            UserProviderPreference: Created/updated preference
            
        Raises:
            ConfigurationError: If provider config not found
        """
        try:
            # Verify provider config exists and is active
            stmt = select(ProviderModelConfig).filter(
                ProviderModelConfig.id == provider_config_id,
                ProviderModelConfig.is_active == True
            )
            result = self.db.execute(stmt)
            provider_config = result.scalar_one_or_none()
            if not provider_config:
                raise ConfigurationError(
                    f"Provider config not found or inactive: {provider_config_id}"
                )
            
            # Update or create preference
            stmt = select(UserProviderPreference).filter(
                UserProviderPreference.user_id == user_id
            )
            result = self.db.execute(stmt)
            preference = result.scalar_one_or_none()
            
            if preference:
                preference.provider_config_id = provider_config_id
            else:
                preference = UserProviderPreference(
                    user_id=user_id,
                    provider_config_id=provider_config_id
                )
                self.db.add(preference)
                
            self.db.commit()
            self.db.refresh(preference)
            return preference
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error setting user provider preference: {e}")
            raise ConfigurationError(
                f"Failed to set user provider preference: {str(e)}"
            )
            
    def clear_user_provider_preference(
        self,
        user_id: UUID
    ) -> None:
        """Clear user's provider preference.
        
        Args:
            user_id: User ID to clear preference for
            
        Raises:
            ConfigurationError: If error occurs while clearing preference
        """
        try:
            stmt = delete(UserProviderPreference).where(
                UserProviderPreference.user_id == user_id
            )
            self.db.execute(stmt)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error clearing user provider preference: {e}")
            raise ConfigurationError(
                f"Failed to clear user provider preference: {str(e)}"
            )
