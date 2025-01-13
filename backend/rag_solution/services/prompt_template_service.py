from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional, List, Dict, Any
from pydantic import ValidationError as PydanticValidationError

from rag_solution.repository.prompt_template_repository import PromptTemplateRepository
from rag_solution.schemas.prompt_template_schema import (
    PromptTemplateInput,
    PromptTemplateOutput,
    PromptTemplateInDB,
    PromptTemplateType
)
from rag_solution.models.prompt_template import PromptTemplate
from core.custom_exceptions import ValidationError, NotFoundError


def _template_to_dict(template: PromptTemplate) -> Dict[str, Any]:
    """Convert a PromptTemplate SQLAlchemy model to a dictionary for Pydantic validation."""
    return {
        "id": template.id,
        "user_id": template.user_id,
        "name": template.name,
        "provider": template.provider,
        "template_type": template.template_type,
        "system_prompt": template.system_prompt,
        "template_format": template.template_format,
        "input_variables": template.input_variables,
        "example_inputs": template.example_inputs,
        "context_strategy": template.context_strategy,
        "max_context_length": template.max_context_length,
        "stop_sequences": template.stop_sequences,
        "validation_schema": template.validation_schema,
        "is_default": template.is_default,
        "created_at": template.created_at,
        "updated_at": template.updated_at
    }


class PromptTemplateService:
    """
    Service layer for managing Prompt Templates.
    Handles template validation, formatting, and repository interaction.
    """

    def __init__(self, db: Session):
        self.repository = PromptTemplateRepository(db)

    # 📝 Template Creation and Updates
    def create_or_update_template(
        self,
        user_id: UUID,
        template: PromptTemplateInput
    ) -> PromptTemplateOutput:
        """
        Create or update a Prompt Template for a user.
        
        Args:
            user_id: User UUID
            template: Template input data
            
        Returns:
            Created/updated template
        """
        prompt_template = self.repository.create_or_update_by_user_id(
            user_id, template
        )
        return PromptTemplateOutput.model_validate(_template_to_dict(prompt_template))

    # 🔍 Template Retrieval
    def get_by_id(self, template_id: UUID) -> Optional[PromptTemplateOutput]:
        """Get a specific template by ID."""
        template = self.repository.get_by_id(template_id)
        if not template:
            return None
        return PromptTemplateOutput.model_validate(_template_to_dict(template))

    def get_user_templates(
        self,
        user_id: UUID
    ) -> List[PromptTemplateOutput]:
        """Get all templates for a specific user."""
        templates = self.repository.get_by_user_id(user_id)
        return [PromptTemplateOutput.model_validate(_template_to_dict(t)) for t in templates]

    def get_by_type(
        self,
        template_type: PromptTemplateType,
        user_id: UUID
    ) -> Optional[PromptTemplateOutput]:
        """
        Get a template by type for a specific user.
        Returns the user's default template of that type.
        """
        template = self.repository.get_user_default_by_type(user_id, template_type)
        if not template:
            # Try to get any template of this type if no default exists
            templates = self.repository.get_by_user_id_and_type(user_id, template_type)
            if templates:
                template = templates[0]  # Use first available template
            else:
                return None
        return PromptTemplateOutput.model_validate(_template_to_dict(template))

    # 🗑️ Template Deletion
    def delete_template(self, user_id: UUID, template_id: UUID) -> bool:
        """Delete a specific template for a user."""
        return self.repository.delete_user_template(user_id, template_id)

    # 🌟 Default Template Management
    def get_user_default(self, user_id: UUID) -> Optional[PromptTemplateOutput]:
        """Get the user's default template."""
        template = self.repository.get_user_default(user_id)
        if not template:
            return None
        return PromptTemplateOutput.model_validate(_template_to_dict(template))

    # 📋 Template Usage
    def format_prompt(
        self,
        template_id: UUID,
        variables: Dict[str, Any]
    ) -> str:
        """
        Format a prompt using a template and variables.
        
        Args:
            template_id: Template UUID
            variables: Variables to substitute in template
            
        Returns:
            Formatted prompt string
            
        Raises:
            NotFoundError: If template not found
            ValidationError: If variables don't match schema
        """
        template = self.repository.get_by_id(template_id)
        if not template:
            raise NotFoundError(f"Template {template_id} not found")

        # Format prompt
        try:
            parts = []
            if template.system_prompt:
                parts.append(template.system_prompt)
            parts.append(template.template_format.format(**variables))
            return "\n\n".join(parts)
        except KeyError as e:
            raise ValidationError(f"Missing required variable: {str(e)}")

    def apply_context_strategy(
        self,
        template_id: UUID,
        contexts: List[str]
    ) -> str:
        """
        Apply a template's context strategy to format multiple context chunks.
        
        Args:
            template_id: Template UUID
            contexts: List of context chunks
            
        Returns:
            Formatted context string
            
        Raises:
            NotFoundError: If template not found
        """
        template = self.repository.get_by_id(template_id)
        if not template:
            raise NotFoundError(f"Template {template_id} not found")

        if not template.context_strategy:
            # Default to simple concatenation
            return "\n\n".join(contexts)

        strategy = template.context_strategy
        max_chunks = strategy.get("max_chunks", len(contexts))
        separator = strategy.get("chunk_separator", "\n\n")
        ordering = strategy.get("ordering", "relevance")
        truncation = strategy.get("truncation", "end")

        # Apply strategy settings
        selected_contexts = contexts[:max_chunks]
        if ordering == "priority":
            # Already ordered by relevance
            pass
        elif ordering == "chronological":
            # Would need metadata for true chronological ordering
            pass

        formatted_contexts = []
        for chunk in selected_contexts:
            if template.max_context_length and len(chunk) > template.max_context_length:
                if truncation == "end":
                    chunk = chunk[:template.max_context_length]
                elif truncation == "start":
                    chunk = chunk[-template.max_context_length:]
                elif truncation == "middle":
                    half = template.max_context_length // 2
                    chunk = chunk[:half] + "..." + chunk[-half:]
            formatted_contexts.append(chunk)

        return separator.join(formatted_contexts)
