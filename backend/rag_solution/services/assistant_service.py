# assistant_service.py

import logging
from typing import List
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session
from pydantic import EmailStr
from rag_solution.repository.assistant_repository import AssistantRepository
from rag_solution.schemas.team_schema import TeamOutput
from rag_solution.schemas.assistant_schema import AssistantInput, AssistantOutput
from rag_solution.services.user_team_service import UserTeamService

logger = logging.getLogger(__name__)


class AssistantService:
    # TO-DO: Remove hacky dependence on UserTeamService
    def __init__(self, db: Session, user_team_service: UserTeamService = None):
        self.assistant_repository = AssistantRepository(db)
        self.user_team_service = user_team_service or UserTeamService(db)

    def create_assistant(self, assistant_input: AssistantInput) -> AssistantOutput:
        try:
            logger.info(f"Creating assistant with input: {assistant_input}")
            assistant = self.assistant_repository.create(assistant_input)
            logger.info(f"Assistant created successfully: {assistant.id}")
            return assistant
        except ValueError as e:
            logger.error(f"Failed to create assistant: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e)) from e

    def get_assistant_by_id(self, assistant_id: UUID) -> AssistantOutput:
        logger.info(f"Fetching assistant with id: {assistant_id}")
        assistant = self.assistant_repository.get_by_id(assistant_id)
        if assistant is None:
            logger.warning(f"Assistant not found: {assistant_id}")
            raise HTTPException(status_code=404, detail="Assistant not found")
        return assistant

    def get_user_assistants(self, ibm_id: str) -> AssistantOutput:
        logger.info(f"Fetching assistant with IBM ID: {user_id}")
        assistant = self.assistant_repository.get_by_id(user_id)
        if assistant is None:
            logger.warning(f"Assistant not found with IBM ID: {user_id}")
            raise HTTPException(status_code=404, detail="Assistant not found")
        return assistant

    def update_assistant(self, assistant_id: UUID, assistant_update: AssistantInput) -> AssistantOutput:
        logger.info(f"Updating assistant {
                    assistant_id} with input: {assistant_update}")
        assistant = self.assistant_repository.update(
            assistant_id, assistant_update)
        if assistant is None:
            logger.warning(f"Assistant not found for update: {assistant_id}")
            raise HTTPException(status_code=404, detail="Assistant not found")
        logger.info(f"Assistant {assistant_id} updated successfully")
        return assistant

    def delete_assistant(self, assistant_id: UUID) -> bool:
        logger.info(f"Deleting assistant: {assistant_id}")
        if not self.assistant_repository.delete(assistant_id):
            logger.warning(f"Assistant not found for deletion: {assistant_id}")
            raise HTTPException(status_code=404, detail="Assistant not found")
        logger.info(f"Assistant {assistant_id} deleted successfully")
        return True

    def list_assistants(self, skip: int = 0, limit: int = 100) -> List[AssistantOutput]:
        logger.info(f"Listing assistants with skip={skip} and limit={limit}")
        try:
            assistants = self.assistant_repository.list_assistants(skip, limit)
            logger.info(f"Retrieved {len(assistants)} assistants")
            return assistants
        except Exception as e:
            logger.error(f"Unexpected error listing assistants: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error") from e

    def query_llm(self):
        """
        Dumb function to simulate a query to a Large Language Model (LLM).

        Returns a dictionary with two keys:
            - query: The query asked to the LLM.
            - answer: The answer given by the LLM.

        The query and answer are hardcoded for demonstration purposes.
        """
        return {
            "query": "What is the meaning of life?",
            "answer": "42"
        }
