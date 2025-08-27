from typing import List
from uuid import UUID
from sqlalchemy.orm import Session
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
        return self.db.query(PromptTemplate).filter_by(id=id).first()

    def get_by_user_id(self, user_id: UUID) -> List[PromptTemplate]:
        return self.db.query(PromptTemplate).filter_by(user_id=user_id).all()
    
    def get_by_user_id_and_type(self, user_id: UUID, template_type: PromptTemplateType) -> List[PromptTemplate]:
        return self.db.query(PromptTemplate).filter_by(user_id=user_id, template_type=template_type).all()

    def delete_user_template(self, user_id: UUID, template_id: UUID) -> bool:
        deleted_count = self.db.query(PromptTemplate).filter_by(user_id=user_id, id=template_id).delete()
        self.db.commit()
        return deleted_count > 0