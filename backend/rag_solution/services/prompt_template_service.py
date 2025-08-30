from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from core.custom_exceptions import NotFoundError, PromptTemplateNotFoundError, ValidationError
from rag_solution.repository.prompt_template_repository import PromptTemplateRepository
from rag_solution.schemas.prompt_template_schema import (
    PromptTemplateBase,
    PromptTemplateInput,
    PromptTemplateOutput,
    PromptTemplateType,
)


class PromptTemplateService:
    def __init__(self, db: Session):
        self.repository = PromptTemplateRepository(db)

    def create_template(self, template: PromptTemplateInput) -> PromptTemplateOutput:
        try:
            prompt_template = self.repository.create_template(template)
            return PromptTemplateOutput.model_validate(prompt_template)
        except Exception as e:
            raise ValidationError(f"Failed to create template: {e!s}") from e

    def get_user_templates(self, user_id: UUID) -> list[PromptTemplateOutput]:
        try:
            templates = self.repository.get_by_user_id(user_id)
            return [PromptTemplateOutput.model_validate(t) for t in templates]
        except Exception as e:
            raise ValidationError(f"Failed to retrieve templates: {e!s}") from e

    def get_by_type(self, user_id: UUID, template_type: PromptTemplateType) -> PromptTemplateOutput | None:
        """Get single template by type and user ID.

        Args:
            template_type: Type of template to retrieve
            user_id: User UUID

        Returns:
            Optional[PromptTemplateOutput]: Template if found
        """
        try:
            templates = self.repository.get_by_user_id_and_type(user_id, template_type)
            if not templates:
                return None
            # Return the default template if exists, otherwise latest by creation date
            default_template = next((t for t in templates if t.is_default), None)
            if default_template:
                return PromptTemplateOutput.model_validate(default_template)
            # Get the latest template by creation date
            latest_template = max(templates, key=lambda t: t.created_at if t.created_at is not None else datetime.min)
            return PromptTemplateOutput.model_validate(latest_template)
        except Exception as e:
            raise ValidationError(f"Failed to retrieve template: {e!s}") from e

    def get_rag_template(self, user_id: UUID) -> PromptTemplateOutput:
        """Get RAG query template for user.

        Args:
            user_id: User UUID

        Returns:
            PromptTemplateOutput: RAG template

        Raises:
            NotFoundError: If template not found
        """
        template = self.get_by_type(user_id, PromptTemplateType.RAG_QUERY)
        if not template:
            raise NotFoundError(
                resource_type="PromptTemplate",
                resource_id=f"RAG_QUERY:{user_id}",
                message="RAG query template not found",
            )
        return template

    def get_question_template(self, user_id: UUID) -> PromptTemplateOutput:
        """Get question generation template for user.

        Args:
            user_id: User UUID

        Returns:
            PromptTemplateOutput: Question generation template

        Raises:
            NotFoundError: If template not found
        """
        template = self.get_by_type(user_id, PromptTemplateType.QUESTION_GENERATION)
        if not template:
            raise NotFoundError(
                resource_type="PromptTemplate",
                resource_id=f"QUESTION_GENERATION:{user_id}",
                message="Question generation template not found",
            )
        return template

    def get_evaluation_template(self, user_id: UUID) -> PromptTemplateOutput | None:
        """Get evaluation template for user if it exists.

        Args:
            user_id: User UUID

        Returns:
            Optional[PromptTemplateOutput]: Evaluation template if found
        """
        return self.get_by_type(user_id, PromptTemplateType.RESPONSE_EVALUATION)

    def get_templates_by_type(self, user_id: UUID, template_type: PromptTemplateType) -> list[PromptTemplateOutput]:
        try:
            templates = self.repository.get_by_user_id_and_type(user_id, template_type)
            return [PromptTemplateOutput.model_validate(t) for t in templates]
        except Exception as e:
            raise ValidationError(f"Failed to retrieve templates by type: {e!s}") from e

    def delete_template(self, user_id: UUID, template_id: UUID) -> bool:
        try:
            self.repository.delete_user_template(user_id, template_id)
            return True
        except Exception as e:
            raise ValidationError(f"Failed to delete template: {e!s}") from e

    def update_template(self, template_id: UUID, template_input: PromptTemplateInput) -> PromptTemplateOutput:
        """Update an existing prompt template.

        Args:
            template_id: UUID of the template to update
            template_input: Updated template data

        Returns:
            PromptTemplateOutput: Updated template

        Raises:
            ValidationError: If update fails
        """
        try:
            updated_template = self.repository.update(template_id, template_input.model_dump(exclude_unset=True))
            return PromptTemplateOutput.model_validate(updated_template)
        except Exception as e:
            raise ValidationError(f"Failed to update template: {e!s}") from e

    def set_default_template(self, template_id: UUID) -> PromptTemplateOutput:
        """Set a template as the default for its type.

        Args:
            template_id: UUID of the template to set as default

        Returns:
            PromptTemplateOutput: Updated template

        Raises:
            ValidationError: If setting default fails
        """
        try:
            template = self.repository.get_by_id(template_id)
            if not template:
                raise NotFoundError(
                    resource_type="PromptTemplate",
                    resource_id=str(template_id)
                )

            # Clear other defaults of the same type for this user
            other_templates = self.repository.get_by_user_id_and_type(template.user_id, template.template_type)
            for other_template in other_templates:
                if other_template.id != template_id and other_template.is_default:
                    self.repository.update(other_template.id, {"is_default": False})

            # Set this template as default
            updated_template = self.repository.update(template_id, {"is_default": True})
            return PromptTemplateOutput.model_validate(updated_template)
        except Exception as e:
            raise ValidationError(f"Failed to set default template: {e!s}") from e

    def format_prompt(self, template_or_id: UUID | PromptTemplateBase, variables: dict[str, Any]) -> str:
        try:
            template = self.repository.get_by_id(template_or_id) if isinstance(template_or_id, UUID) else template_or_id

            if not template:
                raise PromptTemplateNotFoundError(template_id=str(template_or_id))

            parts = []
            if template.system_prompt:
                parts.append(str(template.system_prompt))
            parts.append(template.template_format.format(**variables))
            return "\n\n".join(parts)
        except KeyError as e:
            raise ValidationError(f"Missing required variable: {e!s}") from e
        except Exception as e:
            raise ValidationError(f"Failed to format prompt: {e!s}") from e

    def apply_context_strategy(self, template_id: UUID, contexts: list[str]) -> str:
        """Apply context strategy to format contexts based on template settings."""
        template = self.repository.get_by_id(template_id)
        if not template:
            raise NotFoundError(
                resource_type="PromptTemplate",
                resource_id=str(template_id)
            )
        
        if not template.context_strategy:
            return "\n\n".join(contexts)
        
        strategy = template.context_strategy
        max_chunks = strategy.get("max_chunks", len(contexts))
        separator: str = strategy.get("chunk_separator", "\n\n")
        strategy.get("ordering", "relevance")
        truncation: str = strategy.get("truncation", "end")
        
        selected_contexts = contexts[:max_chunks]
        formatted_contexts = []
        for chunk in selected_contexts:
            if template.max_context_length and len(chunk) > template.max_context_length:
                if truncation == "end":
                    chunk = chunk[: template.max_context_length]
                elif truncation == "start":
                    chunk = chunk[-template.max_context_length :]
                elif truncation == "middle":
                    half = template.max_context_length // 2
                    chunk = chunk[:half] + "..." + chunk[-half:]
            formatted_contexts.append(chunk)
        
        return separator.join(formatted_contexts)
