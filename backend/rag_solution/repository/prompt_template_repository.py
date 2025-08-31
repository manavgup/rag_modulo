from uuid import UUID

from sqlalchemy.orm import Session

from rag_solution.core.exceptions import NotFoundError
from rag_solution.models.prompt_template import PromptTemplate
from rag_solution.schemas.prompt_template_schema import PromptTemplateInput, PromptTemplateType


class PromptTemplateRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_template(self, template: PromptTemplateInput) -> PromptTemplate:
        db_template = PromptTemplate(**template.model_dump(exclude_unset=True))
        self.db.add(db_template)
        self.db.commit()
        self.db.refresh(db_template)
        return db_template

    def get_by_id(self, id: UUID) -> PromptTemplate:
        try:
            template = self.db.query(PromptTemplate).filter_by(id=id).first()
            if not template:
                raise NotFoundError(
                    resource_type="PromptTemplate",
                    resource_id=str(id)
                )
            return template
        except NotFoundError:
            raise
        except Exception as e:
            raise Exception(f"Failed to get template: {e!s}") from e

    def get_by_user_id(self, user_id: UUID) -> list[PromptTemplate]:
        return self.db.query(PromptTemplate).filter_by(user_id=user_id).all()

    def get_by_user_id_and_type(self, user_id: UUID, template_type: PromptTemplateType) -> list[PromptTemplate]:
        return self.db.query(PromptTemplate).filter_by(user_id=user_id, template_type=template_type).all()

    def delete_user_template(self, user_id: UUID, template_id: UUID) -> None:
        """Delete a user's template.

        Raises:
            NotFoundError: If template not found or doesn't belong to user
        """
        try:
            template = self.db.query(PromptTemplate).filter_by(user_id=user_id, id=template_id).first()
            if not template:
                raise NotFoundError(
                    resource_type="PromptTemplate",
                    identifier=f"template {template_id} for user {user_id}"
                )

            self.db.delete(template)
            self.db.commit()
        except NotFoundError:
            raise
        except Exception as e:
            self.db.rollback()
            raise Exception(f"Failed to delete template: {e!s}") from e

    def update(self, template_id: UUID, updates: dict) -> PromptTemplate:
        """Update a prompt template.

        Raises:
            NotFoundError: If template not found
        """
        try:
            template = self.get_by_id(template_id)  # This will raise NotFoundError if not found

            for key, value in updates.items():
                if hasattr(template, key):
                    setattr(template, key, value)

            self.db.commit()
            self.db.refresh(template)
            return template
        except NotFoundError:
            raise
        except Exception as e:
            self.db.rollback()
            raise Exception(f"Failed to update template: {e!s}") from e
