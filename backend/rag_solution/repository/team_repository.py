import logging
from typing import Any

from pydantic import UUID4
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.custom_exceptions import RepositoryError
from rag_solution.core.exceptions import AlreadyExistsError, NotFoundError, ValidationError
from rag_solution.models.team import Team
from rag_solution.schemas.team_schema import TeamInput, TeamOutput
from rag_solution.schemas.user_schema import UserOutput

logger = logging.getLogger(__name__)


class TeamRepository:
    def __init__(self: Any, session: Session) -> None:
        self.session = session

    def create(self, team: TeamInput) -> TeamOutput:
        """Create a new team.

        Raises:
            AlreadyExistsError: If team name already exists
            RepositoryError: For database errors
        """
        try:
            # Check for existing team with same name
            existing_team = self.session.query(Team).filter(Team.name == team.name).first()
            if existing_team:
                raise AlreadyExistsError("Team", "name", team.name)

            db_team = Team(**team.model_dump())
            self.session.add(db_team)
            self.session.commit()
            self.session.refresh(db_team)
            return self._team_to_output(db_team)
        except (AlreadyExistsError, ValidationError):
            self.session.rollback()
            raise
        except IntegrityError as e:
            self.session.rollback()
            if "name" in str(e):
                raise AlreadyExistsError("Team", "name", team.name) from e
            raise ValidationError(f"Integrity constraint violation: {e}") from e
        except Exception as e:
            logger.error(f"Error creating team: {e!s}")
            self.session.rollback()
            raise RepositoryError(f"Failed to create team: {e!s}") from e

    def get(self, team_id: UUID4) -> TeamOutput:
        """Get team by ID.

        Raises:
            NotFoundError: If team not found
            RepositoryError: For database errors
        """
        try:
            team = self.session.query(Team).filter(Team.id == team_id).first()
            if not team:
                raise NotFoundError("Team", resource_id=str(team_id))
            return self._team_to_output(team)
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error getting team {team_id}: {e!s}")
            raise RepositoryError(f"Failed to get team: {e!s}") from e

    def list(self, skip: int = 0, limit: int = 100) -> list[TeamOutput]:
        try:
            logger.debug(f"Attempting to list teams with skip={skip}, limit={limit}")
            teams = self.session.query(Team).offset(skip).limit(limit).all()
            logger.debug(f"Successfully retrieved {len(teams)} teams")
            return [self._team_to_output(team) for team in teams]
        except Exception as e:
            logger.error(f"Error listing teams: {e!s}")
            raise

    def update(self, team_id: UUID4, team_update: TeamInput) -> TeamOutput:
        """Update team.

        Raises:
            NotFoundError: If team not found
            AlreadyExistsError: If new name already exists
            RepositoryError: For database errors
        """
        try:
            team = self.session.query(Team).filter(Team.id == team_id).first()
            if not team:
                raise NotFoundError("Team", resource_id=str(team_id))

            # Check for duplicate name, excluding current team
            existing_team = self.session.query(Team).filter(Team.name == team_update.name, Team.id != team_id).first()
            if existing_team:
                raise AlreadyExistsError("Team", "name", team_update.name)

            for key, value in team_update.model_dump().items():
                setattr(team, key, value)
            self.session.commit()
            self.session.refresh(team)
            return self._team_to_output(team)
        except (NotFoundError, AlreadyExistsError):
            self.session.rollback()
            raise
        except IntegrityError as e:
            self.session.rollback()
            if "name" in str(e):
                raise AlreadyExistsError("Team", "name", team_update.name) from e
            raise ValidationError(f"Integrity constraint violation: {e}") from e
        except Exception as e:
            logger.error(f"Error updating team {team_id}: {e!s}")
            self.session.rollback()
            raise RepositoryError(f"Failed to update team: {e!s}") from e

    def delete(self, team_id: UUID4) -> None:
        """Delete team.

        Raises:
            NotFoundError: If team not found
            RepositoryError: For database errors
        """
        try:
            team = self.session.query(Team).filter(Team.id == team_id).first()
            if not team:
                raise NotFoundError("Team", resource_id=str(team_id))
            self.session.delete(team)
            self.session.commit()
        except NotFoundError:
            raise
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
        )
