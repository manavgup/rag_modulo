from typing import List, Optional
from uuid import UUID, uuid4
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.custom_exceptions import (
    PromptTemplateNotFoundError,
    DuplicatePromptTemplateError,
    InvalidPromptTemplateError
)
from rag_solution.models.prompt_template import PromptTemplate
from rag_solution.schemas.prompt_template_schema import PromptTemplateCreate, PromptTemplateUpdate

class PromptTemplateRepository:
    """Repository for managing prompt templates in the database."""

    def __init__(self, session: Session):
        """Initialize repository with database session.
        
        Args:
            session: SQLAlchemy session
        """
        self._session = session

    def create(self, template: PromptTemplateCreate) -> PromptTemplate:
        """Create a new prompt template.
        
        Args:
            template: Template data
            
        Returns:
            Created template
            
        Raises:
            DuplicatePromptTemplateError: If template with same name and provider exists
        """
        try:
            db_template = PromptTemplate(
                id=str(uuid4()),
                name=template.name,
                provider=template.provider,
                description=template.description,
                system_prompt=template.system_prompt,
                context_prefix=template.context_prefix,
                query_prefix=template.query_prefix,
                answer_prefix=template.answer_prefix,
                is_default=template.is_default,
                input_variables=template.input_variables,
                template_format=template.template_format
            )
            
            # If setting as default, unset any existing default for this provider
            if template.is_default:
                self._unset_default_for_provider(template.provider)
            
            self._session.add(db_template)
            self._session.commit()
            self._session.refresh(db_template)
            return db_template
            
        except IntegrityError:
            self._session.rollback()
            raise DuplicatePromptTemplateError(
                template_name=template.name,
                provider=template.provider
            )

    def get(self, template_id: UUID) -> PromptTemplate:
        """Get prompt template by ID.
        
        Args:
            template_id: Template UUID
            
        Returns:
            Found template
            
        Raises:
            PromptTemplateNotFoundError: If template not found
        """
        template = self._session.query(PromptTemplate).filter(
            PromptTemplate.id == str(template_id)
        ).first()
        
        if not template:
            raise PromptTemplateNotFoundError(template_id=str(template_id))
            
        return template

    def get_by_provider(self, provider: str) -> List[PromptTemplate]:
        """Get all templates for a specific provider.
        
        Args:
            provider: LLM provider name
            
        Returns:
            List of templates
        """
        return self._session.query(PromptTemplate).filter(
            PromptTemplate.provider == provider
        ).all()

    def get_by_name_and_provider(self, name: str, provider: str) -> Optional[PromptTemplate]:
        """Get template by name and provider.
        
        Args:
            name: Template name
            provider: LLM provider name
            
        Returns:
            Template if found, None otherwise
        """
        return self._session.query(PromptTemplate).filter(
            PromptTemplate.name == name,
            PromptTemplate.provider == provider
        ).first()

    def get_default_for_provider(self, provider: str) -> Optional[PromptTemplate]:
        """Get default template for a provider.
        
        Args:
            provider: LLM provider name
            
        Returns:
            Default template if exists, None otherwise
        """
        return self._session.query(PromptTemplate).filter(
            PromptTemplate.provider == provider,
            PromptTemplate.is_default == True
        ).first()

    def list(self) -> List[PromptTemplate]:
        """Get all prompt templates.
        
        Returns:
            List of all templates
        """
        return self._session.query(PromptTemplate).all()

    def update(
        self,
        template_id: UUID,
        template_update: PromptTemplateUpdate
    ) -> PromptTemplate:
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
        try:
            # Get existing template
            db_template = self.get(template_id)
            
            # Update fields
            update_data = template_update.model_dump(exclude_unset=True)
            
            # Handle default flag changes
            if "is_default" in update_data and update_data["is_default"]:
                self._unset_default_for_provider(db_template.provider)
            
            for field, value in update_data.items():
                setattr(db_template, field, value)
            
            self._session.commit()
            self._session.refresh(db_template)
            return db_template
            
        except IntegrityError:
            self._session.rollback()
            raise DuplicatePromptTemplateError(
                template_name=template_update.name,
                provider=db_template.provider
            )

    def delete(self, template_id: UUID) -> None:
        """Delete a prompt template.
        
        Args:
            template_id: Template UUID
            
        Raises:
            PromptTemplateNotFoundError: If template not found
            InvalidPromptTemplateError: If attempting to delete default template
        """
        template = self.get(template_id)
        
        if template.is_default:
            raise InvalidPromptTemplateError(
                template_id=str(template_id),
                reason="Cannot delete default template"
            )
        
        self._session.delete(template)
        self._session.commit()

    def _unset_default_for_provider(self, provider: str) -> None:
        """Unset default flag for all templates of a provider.
        
        Args:
            provider: LLM provider name
        """
        self._session.query(PromptTemplate).filter(
            PromptTemplate.provider == provider,
            PromptTemplate.is_default == True
        ).update({"is_default": False})
        self._session.commit()
