from typing import Any

from pydantic import UUID4
from sqlalchemy.orm import Session

from core.logging_utils import get_logger
from rag_solution.repository.user_team_repository import UserTeamRepository
from rag_solution.schemas.user_team_schema import UserTeamOutput

logger = get_logger(__name__)


class UserTeamService:
    def __init__(self: Any, db: Session) -> None:
        self.db = db
        self.user_team_repository = UserTeamRepository(db)

    def add_user_to_team(self, user_id: UUID4, team_id: UUID4) -> UserTeamOutput | None:
        logger.info(f"Adding user {user_id} to team {team_id}")
        self.user_team_repository.add_user_to_team(user_id, team_id)
        return self.get_user_team(user_id, team_id)

    def remove_user_from_team(self, user_id: UUID4, team_id: UUID4) -> bool:
        logger.info(f"Removing user {user_id} from team {team_id}")
        self.user_team_repository.remove_user_from_team(user_id, team_id)
        return True

    def get_user_teams(self, user_id: UUID4) -> list[UserTeamOutput]:
        logger.info(f"Fetching teams for user {user_id}")
        return self.user_team_repository.get_user_teams(user_id)

    def get_team_users(self, team_id: UUID4) -> list[UserTeamOutput]:
        logger.info(f"Fetching users for team {team_id}")
        return self.user_team_repository.get_team_users(team_id)

    def get_user_team(self, user_id: UUID4, team_id: UUID4) -> UserTeamOutput | None:
        return self.user_team_repository.get_user_team(user_id, team_id)

    def update_user_role_in_team(self, user_id: UUID4, team_id: UUID4, role: str) -> UserTeamOutput | None:
        logger.info(f"Updating role for user {user_id} in team {team_id} to {role}")
        user_team = self.user_team_repository.get_user_team(user_id, team_id)
        if user_team is None:
            logger.error(f"User team not found for user {user_id} in team {team_id}")
            return None
        user_team.role = role
        self.db.commit()
        return user_team
