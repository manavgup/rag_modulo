import json
from typing import List, Optional
from uuid import UUID
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from core.custom_exceptions import (
    PromptTemplateNotFoundError,
    DuplicatePromptTemplateError,
    InvalidPromptTemplateError
)
from rag_solution.models.prompt_template import PromptTemplate
from rag_solution.repository.prompt_template_repository import PromptTemplateRepository
from rag_solution.schemas.prompt_template_schema import (
    PromptTemplateCreate,
    PromptTemplateUpdate,
    PromptTemplateResponse
)

logger = logging.getLogger(__name__)

class PromptTemplateService:
    """Service for managing prompt templates."""

    def __init__(self, session: Session):
        """Initialize service with database session.
        
        Args:
            session: SQLAlchemy session
        """
        self._session = session
        self._repository = PromptTemplateRepository(session)

    def initialize_default_templates(self) -> None:
        """Initialize default templates from prompt_config.json if not exists.
        
        This method reads the prompt_config.json file and creates default templates
        for each provider if they don't already exist.
        """
        config_path = Path(__file__).parent.parent / "config" / "prompt_config.json"
        
        try:
            with open(config_path) as f:
                config = json.load(f)
                
            for provider, template in config.items():
                # Check if default template exists for provider
                existing = self._repository.get_default_for_provider(provider)
                if not existing:
                    # Create default template
                    self._repository.create(PromptTemplateCreate(
                        name=f"{provider}_default",
                        provider=provider,
                        description=f"Default template for {provider}",
                        system_prompt=template["system_prompt"],
                        context_prefix=template["context_prefix"],
                        query_prefix=template["query_prefix"],
                        answer_prefix=template["answer_prefix"],
                        input_variables=template["input_variables"],
                        template_format=template["template_format"],
                        is_default=True
                    ))
                    logger.info(f"Created default template for {provider}")
                    
        except Exception as e:
            logger.error(f"Error initializing default templates: {str(e)}")
            raise

    def create_template(
        self,
        template: PromptTemplateCreate
    ) -> PromptTemplateResponse:
        """Create a new prompt template.
        
        Args:
            template: Template data
            
        Returns:
            Created template
            
        Raises:
            DuplicatePromptTemplateError: If template with same name exists
        """
        db_template = self._repository.create(template)
        return PromptTemplateResponse.model_validate(db_template.to_dict())

    def get_template(
        self,
        template_id: UUID
    ) -> PromptTemplateResponse:
        """Get prompt template by ID.
        
        Args:
            template_id: Template UUID
            
        Returns:
            Found template
            
        Raises:
            PromptTemplateNotFoundError: If template not found
        """
        template = self._repository.get(template_id)
        return PromptTemplateResponse.model_validate(template.to_dict())

    def get_templates_by_provider(
        self,
        provider: str
    ) -> List[PromptTemplateResponse]:
        """Get all templates for a specific provider.
        
        Args:
            provider: LLM provider name
            
        Returns:
            List of templates
        """
        templates = self._repository.get_by_provider(provider)
        return [PromptTemplateResponse.model_validate(t.to_dict()) for t in templates]

    def get_default_template(
        self,
        provider: str
    ) -> Optional[PromptTemplateResponse]:
        """Get default template for a provider.
        
        Args:
            provider: LLM provider name
            
        Returns:
            Default template if exists, None otherwise
        """
        template = self._repository.get_default_for_provider(provider)
        return PromptTemplateResponse.model_validate(template.to_dict()) if template else None

    def list_templates(self) -> List[PromptTemplateResponse]:
        """Get all prompt templates.
        
        Returns:
            List of all templates
        """
        templates = self._repository.list()
        return [PromptTemplateResponse.model_validate(t.to_dict()) for t in templates]

    def update_template(
        self,
        template_id: UUID,
        template_update: PromptTemplateUpdate
    ) -> PromptTemplateResponse:
        """Update an existing prompt template.
        
        Args:
            template_id: Template UUID
            template_update: Update data
            
        Returns:
            Updated template
            
        Raises:
            PromptTemplateNotFoundError: If template not found
            DuplicatePromptTemplateError: If update would create duplicate
        """
        template = self._repository.update(template_id, template_update)
        return PromptTemplateResponse.model_validate(template.to_dict())

    def delete_template(self, template_id: UUID) -> None:
        """Delete a prompt template.
        
        Args:
            template_id: Template UUID
            
        Raises:
            PromptTemplateNotFoundError: If template not found
            InvalidPromptTemplateError: If attempting to delete default template
        """
        self._repository.delete(template_id)

    def create_example_template(
        self,
        provider: str,
        name: Optional[str] = None,
        is_default: bool = False
    ) -> Optional[PromptTemplateResponse]:
        """Create a template using example configuration.
        
        Args:
            provider: LLM provider to get example for
            name: Optional custom name for template
            is_default: Whether to set as default template
            
        Returns:
            Created template if example exists, None otherwise
            
        Raises:
            DuplicatePromptTemplateError: If template with same name exists
        """
        example = PromptTemplate.get_example_template(provider)
        if example:
            template = PromptTemplateCreate(
                name=name or example["name"],
                provider=provider,
                description=example["description"],
                system_prompt=example["system_prompt"],
                context_prefix=example["context_prefix"],
                query_prefix=example["query_prefix"],
                answer_prefix=example["answer_prefix"],
                input_variables=example["input_variables"],
                template_format=example["template_format"],
                is_default=is_default
            )
            return self.create_template(template)
        return None
