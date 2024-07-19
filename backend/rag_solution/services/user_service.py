from uuid import UUID
from typing import Optional, List
from sqlalchemy.orm import Session
from fastapi import Depends
from ..repository.user_repository import UserRepository
from backend.rag_solution.schemas.team_schema import TeamInDB
from backend.rag_solution.schemas.user_schema import UserInput, UserInDB, UserOutput, UserUpdateSchema
from backend.rag_solution.file_management.database import get_db

class UserService:
    def __init__(self, db: Session):
        self.user_repository = UserRepository(db)

    def create_user(self, user: UserInput) -> UserInDB:
        """
        Create a new user.

        Args:
            user (UserInput): The user data to create.

        Returns:
            UserInDB: The created user.
        """
        return self.user_repository.create(user)

    def get_user(self, user_id: UUID) -> Optional[UserOutput]:
        """
        Get a user by their ID.

        Args:
            user_id (UUID): The ID of the user to retrieve.

        Returns:
            Optional[UserOutput]: The user if found, None otherwise.
        """
        return self.user_repository.get_user_output(user_id)

    def get_user_by_ibm_id(self, ibm_id: str) -> Optional[UserOutput]:
        """
        Get a user by their IBM ID.

        Args:
            ibm_id (str): The IBM ID of the user to retrieve.

        Returns:
            Optional[UserOutput]: The user if found, None otherwise.
        """
        user = self.user_repository.get_user_by_ibm_id(ibm_id)
        return UserOutput.model_validate(user) if user else None

    def update_user(self, user_id: UUID, user_update: UserUpdateSchema) -> Optional[UserOutput]:
        """
        Update an existing user.

        Args:
            user_id (UUID): The ID of the user to update.
            user_update (UserUpdateSchema): The update data for the user.

        Returns:
            Optional[UserOutput]: The updated user if found, None otherwise.
        """
        updated_user = self.user_repository.update(user_id, user_update.model_dump(exclude_unset=True))
        return UserOutput.model_validate(updated_user) if updated_user else None

    def delete_user(self, user_id: UUID) -> bool:
        """
        Delete a user.

        Args:
            user_id (UUID): The ID of the user to delete.

        Returns:
            bool: True if the user was deleted, False otherwise.
        """
        return self.user_repository.delete(user_id)

    def get_user_teams(self, user_id: UUID) -> List[TeamInDB]:
        """
        Get all teams a user belongs to.

        Args:
            user_id (UUID): The ID of the user.

        Returns:
            List[TeamInDB]: List of teams the user belongs to.
        """
        return self.user_repository.get_user_teams(user_id)

def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)
