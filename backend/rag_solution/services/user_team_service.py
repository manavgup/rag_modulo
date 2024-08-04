# user_team_service.py

from uuid import UUID
from typing import List
from fastapi import HTTPException
from rag_solution.repository.user_team_repository import UserTeamRepository
from rag_solution.schemas.user_schema import UserOutput
from rag_solution.schemas.user_team_schema import UserTeamInput, UserTeamOutput
import logging

logger = logging.getLogger(__name__)

class UserTeamService:
    def __init__(self, user_team_repository: UserTeamRepository):
        self.user_team_repository = user_team_repository

    def add_user_to_team(self, user_id: UUID, team_id: UUID) -> bool:
        try:
            logger.info(f"Adding user {user_id} to team {team_id}")
            result = self.user_team_repository.add_user_to_team(UserTeamInput(user_id=user_id, team_id=team_id))
            if result:
                logger.info(f"Successfully added user {user_id} to team {team_id}")
            else:
                logger.warning(f"Failed to add user {user_id} to team {team_id}")
            return result
        except Exception as e:
            logger.error(f"Error adding user {user_id} to team {team_id}: {str(e)}")
            if "not present in table" in str(e):
                raise HTTPException(status_code=404, detail="User or team not found")
            raise HTTPException(status_code=500, detail="Internal server error")

    def remove_user_from_team(self, user_id: UUID, team_id: UUID) -> bool:
        try:
            logger.info(f"Removing user {user_id} from team {team_id}")
            result = self.user_team_repository.delete(user_id, team_id)
            if result:
                logger.info(f"Successfully removed user {user_id} from team {team_id}")
            else:
                logger.warning(f"Failed to remove user {user_id} from team {team_id}")
            return result
        except Exception as e:
            logger.error(f"Error removing user {user_id} from team {team_id}: {str(e)}")
            if "not present in table" in str(e):
                raise HTTPException(status_code=404, detail="User or team not found")
            raise HTTPException(status_code=500, detail="Internal server error")

    def get_user_teams(self, user_id: UUID) -> List[UserTeamOutput]:
        try:
            logger.info(f"Fetching teams for user {user_id}")
            user_teams = self.user_team_repository.get_user_teams(user_id)
            logger.info(f"Retrieved {len(user_teams)} teams for user {user_id}")
            return user_teams
        except Exception as e:
            logger.error(f"Error fetching teams for user {user_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")

    def get_team_users(self, team_id: UUID) -> List[UserTeamOutput]:
        try:
            logger.info(f"Fetching users for team {team_id}")
            user_teams = self.user_team_repository.get_team_users(team_id)
            logger.info(f"Retrieved {len(user_teams)} users for team {team_id}")
            return user_teams
        except Exception as e:
            logger.error(f"Error fetching users for team {team_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
