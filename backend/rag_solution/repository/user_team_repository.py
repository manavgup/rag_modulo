from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.logging_utils import get_logger
from rag_solution.models.user_team import UserTeam
from rag_solution.schemas.user_team_schema import UserTeamOutput

logger = get_logger(__name__)


class UserTeamRepository:
    def __init__(self, db: Session):
        self.db = db

    def add_user_to_team(self, user_id: UUID, team_id: UUID) -> bool:
        """Adds a user to a team if not already present. Returns True if successful or if the user is already in the team."""

        existing_entry = (
            self.db.query(UserTeam).filter(UserTeam.user_id == user_id, UserTeam.team_id == team_id).first()
        )

        if existing_entry:
            logger.info(f"User {user_id} is already in team {team_id}. No action needed.")
            return True  # Idempotent behavior

        try:
            db_user_team = UserTeam(user_id=user_id, team_id=team_id)
            self.db.add(db_user_team)
            self.db.commit()
            return True
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"IntegrityError: {e}")
            raise ValueError("User or team not found or duplicate entry")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Unexpected error creating team association: {e!s}")
            raise RuntimeError("Failed to add user to team due to an internal error.")

    def remove_user_from_team(self, user_id: UUID, team_id: UUID) -> bool:
        try:
            result = self.db.query(UserTeam).filter(UserTeam.user_id == user_id, UserTeam.team_id == team_id).delete()
            self.db.commit()
            return result > 0
        except Exception as e:
            logger.error(f"Error removing team association: {e!s}")
            self.db.rollback()
            raise

    def get_user_teams(self, user_id: UUID) -> list[UserTeamOutput]:
        try:
            user_teams = self.db.query(UserTeam).filter(UserTeam.user_id == user_id).all()
            return [UserTeamOutput.model_validate(ut, from_attributes=True) for ut in user_teams]
        except Exception as e:
            logger.error(f"Error listing teams: {e!s}")
            raise

    def get_team_users(self, team_id: UUID) -> list[UserTeamOutput]:
        try:
            user_teams = self.db.query(UserTeam).filter(UserTeam.team_id == team_id).all()
            return [UserTeamOutput.model_validate(ut) for ut in user_teams]
        except Exception as e:
            logger.error(f"Error listing users: {e!s}")
            raise

    def get_user_team(self, user_id: UUID, team_id: UUID) -> UserTeamOutput | None:
        try:
            user_team = self.db.query(UserTeam).filter(UserTeam.user_id == user_id, UserTeam.team_id == team_id).first()
            return UserTeamOutput.model_validate(user_team) if user_team else None
        except Exception as e:
            logger.error(f"Error getting team association: {e!s}")
            raise
