from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional
from rag_solution.models.user_team import UserTeam
from rag_solution.schemas.user_team_schema import UserTeamInput, UserTeamOutput
from rag_solution.schemas.user_schema import UserOutput
from rag_solution.schemas.team_schema import TeamOutput
import logging

logger = logging.getLogger(__name__)

class UserTeamRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, user_team: UserTeamInput) -> UserTeamOutput:
        try:
            db_user_team = UserTeam(user_id=user_team.user_id, team_id=user_team.team_id)
            self.db.add(db_user_team)
            self.db.commit()
            self.db.refresh(db_user_team)
            return self._user_team_to_output(db_user_team)
        except Exception as e:
            logger.error(f"Error creating user-team association: {str(e)}")
            self.db.rollback()
            raise

    def get(self, user_id: UUID, team_id: UUID) -> Optional[UserTeamOutput]:
        try:
            user_team = self.db.query(UserTeam).filter(UserTeam.user_id == user_id, UserTeam.team_id == team_id).first()
            return self._user_team_to_output(user_team) if user_team else None
        except Exception as e:
            logger.error(f"Error getting user-team association: {str(e)}")
            raise

    def delete(self, user_id: UUID, team_id: UUID) -> bool:
        try:
            user_team = self.db.query(UserTeam).filter(UserTeam.user_id == user_id, UserTeam.team_id == team_id).first()
            if user_team:
                self.db.delete(user_team)
                self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting user-team association: {str(e)}")
            self.db.rollback()
            raise

    def list_by_user(self, user_id: UUID) -> List[UserTeamOutput]:
        try:
            user_teams = self.db.query(UserTeam).filter(UserTeam.user_id == user_id).all()
            return [self._user_team_to_output(user_team) for user_team in user_teams]
        except Exception as e:
            logger.error(f"Error listing teams for user {user_id}: {str(e)}")
            raise

    def list_by_team(self, team_id: UUID) -> List[UserTeamOutput]:
        try:
            user_teams = self.db.query(UserTeam).filter(UserTeam.team_id == team_id).all()
            return [self._user_team_to_output(user_team) for user_team in user_teams]
        except Exception as e:
            logger.error(f"Error listing users for team {team_id}: {str(e)}")
            raise

    @staticmethod
    def _user_team_to_output(user_team: UserTeam) -> UserTeamOutput:
        return UserTeamOutput(
            user=UserOutput.model_validate(user_team.user),
            team=TeamOutput.model_validate(user_team.team)
        )
