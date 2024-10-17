import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from rag_solution.models.assistant import Assistant
from rag_solution.schemas.assistant_schema import AssistantInput, AssistantOutput

logger = logging.getLogger(__name__)

class AssistantRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, assistant: AssistantInput) -> AssistantOutput:
        print("Assistant2: ", assistant)
        try:
            db_assistant = Assistant(
                query = assistant.query,
                context = assistant.context,
                max_tokens = assistant.max_tokens,
                response = assistant.response,
                confidence = assistant.confidence,
                error = assistant.error,
                user_id = assistant.user_id
            )
            self.db.add(db_assistant)
            self.db.commit()
            self.db.flush()
            self.db.refresh(db_assistant)
            return self._assistant_to_output(db_assistant)
        except IntegrityError as e:
            self.db.rollback()
            raise ValueError(f"An error occurred while creating the assistant {e}") from e

    def update(self, assistant_id: UUID, assistant_update: AssistantInput) -> Optional[AssistantInput]:
        try:
            assistant = self.db.query(Assistant).filter(Assistant.id == assistant_id).first()
            if assistant:
                for key, value in assistant_update.model_dump().items():
                    setattr(assistant, key, value)
                self.db.commit()
                self.db.refresh(assistant)
                return assistant_update
            return None
        except Exception as e:
            logger.error(f"Error updating assistant {assistant_id}: {str(e)}")
            self.db.rollback()
            raise
        
    def get_by_id(self, assistant_id: UUID) -> Optional[AssistantOutput]:
        try:
            assistant = self.db.query(Assistant).filter(Assistant.id == assistant_id).first()
            return self._assistant_to_output(assistant) if assistant else None
        except Exception as e:
            logger.error(f"Error getting assistant {assistant_id}: {str(e)}")
            raise

    def delete(self, assistant_id: UUID) -> bool:
        try:
            assistant = self.db.query(Assistant).filter(Assistant.id == assistant_id).first()
            if assistant:
                self.db.delete(assistant)
                self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting assistant {assistant_id}: {str(e)}")
            self.db.rollback()
            raise

    def list_assistants(self, skip: int = 0, limit: int = 100) -> List[AssistantOutput]:
        try:
            assistants = self.db.query(Assistant).offset(skip).limit(limit).all()
            return [self._assistant_to_output(assistant) for assistant in assistants]
        except Exception as e:
            logger.error(f"Error listing assistants: {str(e)}")
            raise

    @staticmethod
    def _assistant_to_output(assistant: Assistant) -> AssistantOutput:
        return AssistantOutput(
            id=assistant.id,
            query=assistant.query,
            context=assistant.context,
            max_tokens=assistant.max_tokens,
            response=assistant.response,
            confidence=assistant.confidence,
            error=assistant.error,
            user_id=assistant.user_id
        )

