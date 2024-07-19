from uuid import UUID
from typing import Optional, List
from sqlalchemy.orm import Session
from fastapi import Depends
from backend.rag_solution.repository.team_repository import TeamRepository
from backend.rag_solution.schemas.team_schema import TeamInput, TeamInDB, TeamOutput, UserTeamInDB, TeamUpdateSchema
from backend.rag_solution.file_management.database import get_db

class TeamService:
    def __init__(self, db: Session):
        self.team_repository = TeamRepository(db)

    def create_team(self, team: TeamInput) -> TeamInDB:
        """
        Create a new team.

        Args:
            team (TeamInput): The team data to create.

        Returns:
            TeamInDB: The created team.
        """
        return self.team_repository.create(team)

    def get_team(self, team_id: UUID) -> Optional[TeamOutput]:
        """
        Get a team by its ID.

        Args:
            team_id (UUID): The ID of the team to retrieve.

        Returns:
            Optional[TeamOutput]: The team if found, None otherwise.
        """
        return self.team_repository.get_team_output(team_id)

    def get_all_teams(self, skip: int = 0, limit: int = 100) -> List[TeamInDB]:
        """
        Get all teams with pagination.

        Args:
            skip (int): Number of teams to skip.
            limit (int): Maximum number of teams to return.

        Returns:
            List[TeamInDB]: List of teams.
        """
        return self.team_repository.list(skip, limit)

    def update_team(self, team_id: UUID, team_update: TeamUpdateSchema) -> Optional[TeamInDB]:
        """
        Update an existing team.

        Args:
            team_id (UUID): The ID of the team to update.
            team_update (TeamUpdateSchema): The update data for the team.

        Returns:
            Optional[TeamInDB]: The updated team if found, None otherwise.
        """
        return self.team_repository.update(team_id, team_update.model_dump(exclude_unset=True))

    def delete_team(self, team_id: UUID) -> bool:
        """
        Delete a team.

        Args:
            team_id (UUID): The ID of the team to delete.

        Returns:
            bool: True if the team was deleted, False otherwise.
        """
        return self.team_repository.delete(team_id)

    def add_user_to_team(self, user_id: UUID, team_id: UUID) -> Optional[UserTeamInDB]:
        """
        Add a user to a team.

        Args:
            user_id (UUID): The ID of the user to add.
            team_id (UUID): The ID of the team to add the user to.

        Returns:
            Optional[UserTeamInDB]: The created UserTeam association if successful, None otherwise.
        """
        return self.team_repository.add_user_to_team(user_id, team_id)

    def remove_user_from_team(self, user_id: UUID, team_id: UUID) -> bool:
        """
        Remove a user from a team.

        Args:
            user_id (UUID): The ID of the user to remove.
            team_id (UUID): The ID of the team to remove the user from.

        Returns:
            bool: True if the user was removed from the team, False otherwise.
        """
        return self.team_repository.remove_user_from_team(user_id, team_id)

    def get_team_users(self, team_id: UUID) -> List[UserTeamInDB]:
        """
        Get all users in a team.

        Args:
            team_id (UUID): The ID of the team.

        Returns:
            List[UserTeamInDB]: List of UserTeam associations for the given team.
        """
        return self.team_repository.get_team_users(team_id)

    def get_user_teams(self, user_id: UUID) -> List[TeamInDB]:
        """
        Get all teams a user belongs to.

        Args:
            user_id (UUID): The ID of the user.

        Returns:
            List[TeamInDB]: List of teams the user belongs to.
        """
        return self.team_repository.get_user_teams(user_id)

    def team_exists(self, team_id: UUID) -> bool:
        """
        Check if a team exists.

        Args:
            team_id (UUID): The ID of the team to check.

        Returns:
            bool: True if the team exists, False otherwise.
        """
        return self.team_repository.team_exists(team_id)

    def user_in_team(self, user_id: UUID, team_id: UUID) -> bool:
        """
        Check if a user is in a team.

        Args:
            user_id (UUID): The ID of the user.
            team_id (UUID): The ID of the team.

        Returns:
            bool: True if the user is in the team, False otherwise.
        """
        return self.team_repository.user_in_team(user_id, team_id)

def get_team_service(db: Session = Depends(get_db)) -> TeamService:
    return TeamService(db)
