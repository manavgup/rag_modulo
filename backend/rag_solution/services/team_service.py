# team_service.py

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from rag_solution.repository.team_repository import TeamRepository
from rag_solution.schemas.team_schema import TeamInput, TeamOutput
from rag_solution.schemas.user_schema import UserOutput
from rag_solution.schemas.user_team_schema import UserTeamOutput
from rag_solution.services.user_service import UserService
from rag_solution.services.user_team_service import UserTeamService

logger = logging.getLogger(__name__)


class TeamService:
    def __init__(self, db: Session, user_team_service: UserTeamService = None, user_service: UserService = None):
        self.team_repository = TeamRepository(db)
        self.user_team_service = user_team_service or UserTeamService(db)
        self.user_service = user_service

    def create_team(self, team_input: TeamInput) -> TeamOutput:
        logger.info(f"Creating team with input: {team_input}")
        team = self.team_repository.create(team_input)
        logger.info(f"Team created successfully: {team.id}")
        return team

    def get_team_by_id(self, team_id: UUID) -> TeamOutput:
        logger.info(f"Fetching team with id: {team_id}")
        return self.team_repository.get(team_id)  # Will raise NotFoundError if not found

    def update_team(self, team_id: UUID, team_update: TeamInput) -> TeamOutput:
        logger.info(f"Updating team {team_id} with input: {team_update}")
        team = self.team_repository.update(team_id, team_update)  # Will raise NotFoundError if not found
        logger.info(f"Team {team_id} updated successfully")
        return team

    def delete_team(self, team_id: UUID) -> bool:
        try:
            logger.info(f"Deleting team: {team_id}")
            self.team_repository.delete(team_id)
            logger.info(f"Team {team_id} deleted successfully")
            return True
        except Exception as e:
            logger.error(f"Unexpected error deleting team {team_id}: {e!s}")
            raise

    def get_team_users(self, team_id: UUID) -> list[UserOutput]:
        logger.info(f"Fetching users for team: {team_id}")
        user_teams = self.user_team_service.get_team_users(team_id)

        if not self.user_service:
            logger.warning("UserService not provided, returning empty list")
            return []

        # Convert UserTeamOutput to UserOutput by fetching actual user data
        users = []
        for user_team in user_teams:
            try:
                user = self.user_service.get_user_by_id(user_team.user_id)
                users.append(user)
            except Exception as e:
                logger.warning(f"Failed to fetch user {user_team.user_id}: {e}")
                continue
        return users

    def add_user_to_team(self, user_id: UUID, team_id: UUID) -> UserTeamOutput:
        logger.info(f"Adding user {user_id} to team {team_id}")
        return self.user_team_service.add_user_to_team(user_id, team_id)

    def remove_user_from_team(self, user_id: UUID, team_id: UUID) -> bool:
        logger.info(f"Removing user {user_id} from team {team_id}")
        return self.user_team_service.remove_user_from_team(user_id, team_id)

    def list_teams(self, skip: int = 0, limit: int = 100) -> list[TeamOutput]:
        logger.info(f"Listing teams with skip={skip} and limit={limit}")
        try:
            teams = self.team_repository.list(skip, limit)
            logger.info(f"Retrieved {len(teams)} teams")
            return teams
        except Exception as e:
            logger.error(f"Unexpected error listing teams: {e!s}")
            raise
