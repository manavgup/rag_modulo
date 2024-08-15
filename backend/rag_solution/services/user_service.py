# user_service.py

import logging
from typing import List
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.rag_solution.repository.user_repository import UserRepository
from backend.rag_solution.schemas.team_schema import TeamOutput
from backend.rag_solution.schemas.user_schema import UserInput, UserOutput
from backend.rag_solution.services.user_team_service import UserTeamService

logger = logging.getLogger(__name__)

class UserService:
    # TO-DO: Remove hacky dependence on UserTeamService
    def __init__(self, db: Session, user_team_service: UserTeamService = None):
        self.user_repository = UserRepository(db)
        self.user_team_service = user_team_service or UserTeamService(db)

    def create_user(self, user_input: UserInput) -> UserOutput:
        try:
            logger.info(f"Creating user with input: {user_input}")
            user = self.user_repository.create(user_input)
            logger.info(f"User created successfully: {user.id}")
            return user
        except ValueError as e:
            logger.error(f"Failed to create user: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))

    def get_user_by_id(self, user_id: UUID) -> UserOutput:
        logger.info(f"Fetching user with id: {user_id}")
        user = self.user_repository.get_by_id(user_id)
        if user is None:
            logger.warning(f"User not found: {user_id}")
            raise HTTPException(status_code=404, detail="User not found")
        return user

    def get_user_by_ibm_id(self, ibm_id: str) -> UserOutput:
        logger.info(f"Fetching user with IBM ID: {ibm_id}")
        user = self.user_repository.get_user_by_ibm_id(ibm_id)
        if user is None:
            logger.warning(f"User not found with IBM ID: {ibm_id}")
            raise HTTPException(status_code=404, detail="User not found")
        return user

    def update_user(self, user_id: UUID, user_update: UserInput) -> UserOutput:
        logger.info(f"Updating user {user_id} with input: {user_update}")
        user = self.user_repository.update(user_id, user_update)
        if user is None:
            logger.warning(f"User not found for update: {user_id}")
            raise HTTPException(status_code=404, detail="User not found")
        logger.info(f"User {user_id} updated successfully")
        return user

    def delete_user(self, user_id: UUID) -> bool:
        logger.info(f"Deleting user: {user_id}")
        if not self.user_repository.delete(user_id):
            logger.warning(f"User not found for deletion: {user_id}")
            raise HTTPException(status_code=404, detail="User not found")
        logger.info(f"User {user_id} deleted successfully")
        return True

    def get_user_teams(self, user_id: UUID) -> List[TeamOutput]:
        logger.info(f"Fetching teams for user: {user_id}")
        return self.user_team_service.get_user_teams(user_id)

    def list_users(self, skip: int = 0, limit: int = 100) -> List[UserOutput]:
        logger.info(f"Listing users with skip={skip} and limit={limit}")
        try:
            users = self.user_repository.list_users(skip, limit)
            logger.info(f"Retrieved {len(users)} users")
            return users
        except Exception as e:
            logger.error(f"Unexpected error listing users: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
