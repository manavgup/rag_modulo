"""Repository for managing Prompt Templates in the database."""
from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID

from rag_solution.models.prompt_template import PromptTemplate
from rag_solution.schemas.prompt_template_schema import PromptTemplateInput, PromptTemplateType


class PromptTemplateRepository:
    """
    Repository for managing Prompt Templates in the database.
    Provides CRUD operations and utility methods.
    """

    def __init__(self, db: Session):
        self.db = db

    # 📝 Create or Update by User ID
    def create_or_update_by_user_id(self, user_id: UUID, template: PromptTemplateInput) -> PromptTemplate:
        """Create or update a Prompt Template for a specific user."""
        db_template = (
            self.db.query(PromptTemplate)
            .filter(PromptTemplate.user_id == user_id)
            .filter(PromptTemplate.name == template.name)
            .first()
        )

        if db_template:
            # Update existing - exclude user_id to avoid conflicts
            for field, value in template.model_dump(exclude={"user_id"}, exclude_unset=True).items():
                setattr(db_template, field, value)
        else:
            # Create new
            db_template = PromptTemplate(
                user_id=user_id,
                name=template.name,
                provider=template.provider,
                template_type=template.template_type,
                system_prompt=template.system_prompt,
                template_format=template.template_format,
                input_variables=template.input_variables,
                example_inputs=template.example_inputs,
                context_strategy=template.context_strategy,
                max_context_length=template.max_context_length,
                stop_sequences=template.stop_sequences,
                is_default=template.is_default
            )

        self.db.add(db_template)
        self.db.commit()
        self.db.refresh(db_template)
        return db_template

    # 🔍 Get by ID
    def get_by_id(self, id: UUID) -> Optional[PromptTemplate]:
        """Fetch a Prompt Template by ID."""
        return self.db.query(PromptTemplate).filter(PromptTemplate.id == id).first()

    # 🔍 Get by User ID
    def get_by_user_id(self, user_id: UUID) -> List[PromptTemplate]:
        """Fetch all Prompt Templates for a user."""
        return (
            self.db.query(PromptTemplate)
            .filter(PromptTemplate.user_id == user_id)
            .all()
        )

    def get_by_user_id_and_type(self, user_id: UUID, template_type: PromptTemplateType) -> List[PromptTemplate]:
        """Fetch all Prompt Templates for a user of a specific type."""
        return (
            self.db.query(PromptTemplate)
            .filter(PromptTemplate.user_id == user_id)
            .filter(PromptTemplate.template_type == template_type)
            .all()
        )

    # 🌟 Get User's Default Template
    def get_user_default(self, user_id: UUID) -> Optional[PromptTemplate]:
        """Fetch the default Prompt Template for a user."""
        return (
            self.db.query(PromptTemplate)
            .filter(PromptTemplate.user_id == user_id)
            .filter(PromptTemplate.is_default == True)
            .first()
        )

    # 🔍 Get User's Default Template by Type
    def get_user_default_by_type(self, user_id: UUID, template_type: PromptTemplateType) -> Optional[PromptTemplate]:
        """Fetch a user's default template of a specific type."""
        return (
            self.db.query(PromptTemplate)
            .filter(PromptTemplate.user_id == user_id)
            .filter(PromptTemplate.template_type == template_type)
            .filter(PromptTemplate.is_default == True)
            .first()
        )

    # 🔍 Get User's Templates by Provider
    def get_user_templates_by_provider(self, user_id: UUID, provider: str) -> List[PromptTemplate]:
        """Fetch a user's templates for a specific provider."""
        return (
            self.db.query(PromptTemplate)
            .filter(PromptTemplate.user_id == user_id)
            .filter(PromptTemplate.provider == provider)
            .all()
        )

    # 🛠️ Update
    def update(self, id: UUID, template: PromptTemplateInput) -> Optional[PromptTemplate]:
        """Update an existing Prompt Template."""
        db_template = self.get_by_id(id)
        if not db_template:
            return None

        # Update fields - exclude user_id to avoid conflicts
        for field, value in template.model_dump(exclude={"user_id"}, exclude_unset=True).items():
            setattr(db_template, field, value)

        self.db.commit()
        self.db.refresh(db_template)
        return db_template

    # 🗑️ Delete by ID
    def delete(self, id: UUID) -> bool:
        """Delete a Prompt Template by ID."""
        db_template = self.get_by_id(id)
        if not db_template:
            return False

        self.db.delete(db_template)
        self.db.commit()
        return True

    # 🗑️ Delete User Template
    def delete_user_template(self, user_id: UUID, template_id: UUID) -> bool:
        """Delete a specific template for a user."""
        result = (
            self.db.query(PromptTemplate)
            .filter(PromptTemplate.user_id == user_id)
            .filter(PromptTemplate.id == template_id)
            .delete()
        )
        self.db.commit()
        return result > 0
