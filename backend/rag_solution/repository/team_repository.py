import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from backend.rag_solution.models.team import Team
from backend.rag_solution.schemas.team_schema import TeamInput, TeamOutput
from backend.rag_solution.schemas.user_schema import UserOutput

logger = logging.getLogger(__name__)

class TeamRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, team: TeamInput) -> TeamOutput:
        try:
            db_team = Team(**team.model_dump())
            self.session.add(db_team)
            self.session.commit()
            self.session.refresh(db_team)
            return self._team_to_output(db_team)
        except Exception as e:
            logger.error(f"Error creating team: {str(e)}")
            self.session.rollback()
            raise

    def get(self, team_id: UUID) -> Optional[TeamOutput]:
        try:
            team = self.session.query(Team).filter(Team.id == team_id).first()
            return self._team_to_output(team) if team else None
        except Exception as e:
            logger.error(f"Error getting team {team_id}: {str(e)}")
            raise

    def list(self, skip: int = 0, limit: int = 100) -> List[TeamOutput]:
        try:
            teams = self.session.query(Team).offset(skip).limit(limit).all()
            return [self._team_to_output(team) for team in teams]
        except Exception as e:
            logger.error(f"Error listing teams: {str(e)}")
            raise

    def update(self, team_id: UUID, team_update: TeamInput) -> TeamInput:
        try:
            team = self.session.query(Team).filter(Team.id == team_id).first()
            if team:
                for key, value in team_update.model_dump().items():
                    setattr(team, key, value)
                self.session.commit()
                self.session.refresh(team)
                return team_update
            return None
        except Exception as e:
            logger.error(f"Error updating team {team_id}: {str(e)}")
            self.session.rollback()
            raise

    def delete(self, team_id: UUID) -> bool:
        try:
            team = self.session.query(Team).filter(Team.id == team_id).first()
            if team:
                self.session.delete(team)
                self.session.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting team {team_id}: {str(e)}")
            self.session.rollback()
            raise

    @staticmethod
    def _team_to_output(team: Team) -> TeamOutput:
        return TeamOutput(
            id=team.id,
            name=team.name,
            description=team.description,
            users=[UserOutput.model_validate(user) for user in team.users],
            created_at=team.created_at,
            updated_at=team.updated_at
        )
