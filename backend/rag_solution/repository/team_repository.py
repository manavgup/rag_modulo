import logging
from uuid import UUID

from sqlalchemy.orm import Session

from core.custom_exceptions import DuplicateEntryError, RepositoryError
from rag_solution.models.team import Team
from rag_solution.schemas.team_schema import TeamInput, TeamOutput
from rag_solution.schemas.user_schema import UserOutput

logger = logging.getLogger(__name__)


class TeamRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, team: TeamInput) -> TeamOutput:
        try:
            # Check for existing team with same name
            existing_team = self.session.query(Team).filter(Team.name == team.name).first()
            if existing_team:
                raise ValueError(f"Team with name '{team.name}' already exists")

            db_team = Team(**team.model_dump())
            self.session.add(db_team)
            self.session.commit()
            self.session.refresh(db_team)
            return self._team_to_output(db_team)
        except Exception as e:
            logger.error(f"Error creating team: {e!s}")
            self.session.rollback()
            raise

    def get(self, team_id: UUID) -> TeamOutput | None:
        try:
            team = self.session.query(Team).filter(Team.id == team_id).first()
            return self._team_to_output(team) if team else None
        except Exception as e:
            logger.error(f"Error getting team {team_id}: {e!s}")
            raise

    def list(self, skip: int = 0, limit: int = 100) -> list[TeamOutput]:
        try:
            logger.debug(f"Attempting to list teams with skip={skip}, limit={limit}")
            teams = self.session.query(Team).offset(skip).limit(limit).all()
            logger.debug(f"Successfully retrieved {len(teams)} teams")
            return [self._team_to_output(team) for team in teams]
        except Exception as e:
            logger.error(f"Error listing teams: {e!s}")
            raise

    def update(self, team_id: UUID, team_update: TeamInput) -> TeamOutput:  # Changed return type
        try:
            team = self.session.query(Team).filter(Team.id == team_id).first()
            if team:
                # Check for duplicate name, excluding current team
                existing_team = (
                    self.session.query(Team).filter(Team.name == team_update.name, Team.id != team_id).first()
                )
                if existing_team:
                    raise DuplicateEntryError(
                        param_name="Team", message=f"Team with name '{team_update.name}' already exists"
                    )

                for key, value in team_update.model_dump().items():
                    setattr(team, key, value)
                self.session.commit()
                self.session.refresh(team)
                return self._team_to_output(team)  # Return TeamOutput instead of TeamInput
            return None
        except Exception as e:
            logger.error(f"Error updating team {team_id}: {e!s}")
            self.session.rollback()
            raise RepositoryError(f"Failed to update team: {e!s}") from e

    def delete(self, team_id: UUID) -> bool:
        try:
            team = self.session.query(Team).filter(Team.id == team_id).first()
            if team:
                self.session.delete(team)
                self.session.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting team {team_id}: {e!s}")
            self.session.rollback()
            raise RepositoryError(f"Failed to delete team: {e!s}") from e

    @staticmethod
    def _team_to_output(team: Team) -> TeamOutput:
        return TeamOutput(
            id=team.id,
            name=team.name,
            description=team.description,
            users=[UserOutput.model_validate(user) for user in team.users],
            created_at=team.created_at,
            updated_at=team.updated_at,
        )
