from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID
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
from core.logging_utils import get_logger

logger = get_logger("services.prompt_template")


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
        self.db = db
        self.repository = PromptTemplateRepository(db)

    # 📝 Template Creation and Updates
    def initialize_default_templates(
        self,
        user_id: UUID,
        provider_name: str
    ) -> Tuple[PromptTemplateOutput, PromptTemplateOutput]:
        """
        Initialize default prompt templates for a new user.
        
        Args:
            user_id: User's UUID
            provider_name: Name of the LLM provider (e.g., 'watsonx')
            
        Returns:
            Tuple of (rag_template, question_template)
        """
        logger.info(f"Initializing default templates for user {user_id}")

        # Check if templates already exist
        rag_template = self.get_by_type(PromptTemplateType.RAG_QUERY, user_id)
        question_template = self.get_by_type(PromptTemplateType.QUESTION_GENERATION, user_id)

        if rag_template and question_template:
            logger.info("Default templates already exist for user")
            return rag_template, question_template

        # Create RAG query template if needed
        if not rag_template:
            logger.info("Creating default RAG template")
            rag_template = self.create_or_update_template(
                user_id,
                PromptTemplateInput(
                    name="default-rag-template",
                    provider=provider_name,
                    template_type=PromptTemplateType.RAG_QUERY,
                    system_prompt="You are a helpful AI assistant specializing in answering questions based on the given context.",
                    template_format="{context}\n\n{question}",
                    input_variables={
                        "context": "Retrieved context for answering the question",
                        "question": "User's question to answer"
                    },
                    example_inputs={
                        "context": "Python was created by Guido van Rossum.",
                        "question": "Who created Python?"
                    },
                    is_default=True,
                    validation_schema={
                        "model": "PromptVariables",
                        "fields": {
                            "context": {"type": "str", "min_length": 1},
                            "question": {"type": "str", "min_length": 1}
                        },
                        "required": ["context", "question"]
                    }
                )
            )

        # Create question generation template if needed
        if not question_template:
            logger.info("Creating default question generation template")
            question_template = self.create_or_update_template(
                user_id,
                PromptTemplateInput(
                    name="default-question-template",
                    provider=provider_name,
                    template_type=PromptTemplateType.QUESTION_GENERATION,
                    system_prompt=(
                        "You are an AI assistant that generates relevant questions based on "
                        "the given context. Generate clear, focused questions that can be "
                        "answered using the information provided."
                    ),
                    template_format=(
                        "{context}\n\n"
                        "Generate {num_questions} specific questions that can be answered "
                        "using only the information provided above."
                    ),
                    input_variables={
                        "context": "Retrieved passages from knowledge base",
                        "num_questions": "Number of questions to generate"
                    },
                    example_inputs={
                        "context": "Python supports multiple programming paradigms.",
                        "num_questions": 3
                    },
                    is_default=True,
                    validation_schema={
                        "model": "PromptVariables",
                        "fields": {
                            "context": {"type": "str", "min_length": 1},
                            "num_questions": {"type": "int", "gt": 0}
                        },
                        "required": ["context", "num_questions"]
                    }
                )
            )

        logger.info(f"Successfully initialized default templates for user {user_id}")
        return rag_template, question_template

    def create_template(
        self,
        template: PromptTemplateInput
    ) -> PromptTemplateOutput:
        """
        Create a new Prompt Template.
        
        Args:
            template: Template input data
            
        Returns:
            Created template
        """
        prompt_template = self.repository.create(template)
        return PromptTemplateOutput.model_validate(_template_to_dict(prompt_template))

    def update_template(
        self,
        template_id: UUID,
        updates: Dict[str, Any]
    ) -> PromptTemplateOutput:
        """
        Update an existing Prompt Template.
        
        Args:
            template_id: Template UUID to update
            updates: Dictionary of fields to update
            
        Returns:
            Updated template
            
        Raises:
            NotFoundError: If template not found
        """
        template = self.repository.get_by_id(template_id)
        if not template:
            raise NotFoundError(f"Template {template_id} not found")
        
        updated_template = self.repository.update(template_id, updates)
        return PromptTemplateOutput.model_validate(_template_to_dict(updated_template))

    def set_default_template(
        self,
        template_id: UUID
    ) -> PromptTemplateOutput:
        """
        Set a template as default.
        
        Args:
            template_id: Template UUID to set as default
            
        Returns:
            Updated template
            
        Raises:
            NotFoundError: If template not found
        """
        template = self.repository.get_by_id(template_id)
        if not template:
            raise NotFoundError(f"Template {template_id} not found")
        
        # Reset other default templates for the same user and type
        self.repository.reset_user_default_templates(template.user_id, template.template_type)
        
        # Set this template as default
        updated_template = self.repository.update(template_id, {"is_default": True})
        return PromptTemplateOutput.model_validate(_template_to_dict(updated_template))

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
