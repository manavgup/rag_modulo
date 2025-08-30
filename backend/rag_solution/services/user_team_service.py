from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from core.logging_utils import get_logger
from rag_solution.repository.user_team_repository import UserTeamRepository
from rag_solution.schemas.user_team_schema import UserTeamInput, UserTeamOutput

logger = get_logger(__name__)


class UserTeamService:
    def __init__(self, db: Session):
        self.db = db
        self.user_team_repository = UserTeamRepository(db)

    def add_user_to_team(self, user_id: UUID, team_id: UUID) -> UserTeamOutput:
        try:
            logger.info(f"Adding user {user_id} to team {team_id}")
            success = self.user_team_repository.add_user_to_team(user_id, team_id)
            if success:
                # Return the created user-team association
                return self.get_user_team(user_id, team_id)
            else:
                raise HTTPException(status_code=500, detail="Failed to add user to team")
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except Exception as e:
            logger.error(f"Error adding user to team: {e!s}")
            raise HTTPException(status_code=500, detail="Internal server error") from e

    def remove_user_from_team(self, user_id: UUID, team_id: UUID) -> bool:
        logger.info(f"Removing user {user_id} from team {team_id}")
        try:
            self.user_team_repository.remove_user_from_team(user_id, team_id)
            return True
        except Exception as e:
            logger.error(f"Error removing user from team: {e}")
            raise HTTPException(status_code=404, detail="User or team not found") from e

    def get_user_teams(self, user_id: UUID) -> list[UserTeamOutput]:
        try:
            logger.info(f"Fetching teams for user {user_id}")
            return self.user_team_repository.get_user_teams(user_id)
        except Exception as e:
            logger.error(f"Error fetching teams: {e!s}")
            raise HTTPException(status_code=500, detail="Internal server error") from e

    def get_team_users(self, team_id: UUID) -> list[UserTeamOutput]:
        try:
            logger.info(f"Fetching users for team {team_id}")
            return self.user_team_repository.get_team_users(team_id)
        except Exception as e:
            logger.error(f"Error fetching users: {e!s}")
            raise HTTPException(status_code=500, detail="Internal server error") from e

    def get_user_team(self, user_id: UUID, team_id: UUID) -> UserTeamOutput:
        try:
            user_team = self.user_team_repository.get_user_team(user_id, team_id)
            if user_team is None:
                raise HTTPException(status_code=404, detail="Team association not found")
            return user_team
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching team association: {e!s}")
            raise HTTPException(status_code=500, detail="Internal server error") from e

    def update_user_role_in_team(self, user_id: UUID, team_id: UUID, role: str) -> UserTeamOutput:
        try:
            logger.info(f"Updating role for user {user_id} in team {team_id} to {role}")
            user_team = self.user_team_repository.get_user_team(user_id, team_id)
            if not user_team:
                raise HTTPException(status_code=404, detail="Team association not found")

            user_team.role = role
            self.db.commit()
            return user_team
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating user role: {e!s}")
            self.db.rollback()
            raise HTTPException(status_code=500, detail="Internal server error") from e
