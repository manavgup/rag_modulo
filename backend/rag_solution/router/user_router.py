from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.rag_solution.file_management.database import get_db
from backend.rag_solution.schemas.user_schema import UserInput, UserOutput
from backend.rag_solution.services.user_service import UserService

router = APIRouter()

@router.post("/", response_model=UserOutput)
def create_user(user: UserInput, db: Session = Depends(get_db)) -> UserOutput:
    """
    Create a new user.

    Args:
        user (UserInput): The input data for creating a user.
        db (Session): The database session.

    Returns:
        UserOutput: The created user.
    """
    user_service = UserService(db)
    return user_service.create_user(user)

@router.get("/{user_id}", response_model=UserOutput)
def get_user(user_id: UUID, db: Session = Depends(get_db)) -> UserOutput:
    """
    Get a user by their ID.

    Args:
        user_id (UUID): The ID of the user to retrieve.
        db (Session): The database session.

    Returns:
        UserOutput: The retrieved user.
    """
    user_service = UserService(db)
    return user_service.get_user_by_id(user_id)

@router.put("/{user_id}", response_model=UserOutput)
def update_user(user_id: UUID, user_update: UserInput, db: Session = Depends(get_db)) -> UserOutput:
    """
    Update a user.

    Args:
        user_id (UUID): The ID of the user to update.
        user_update (UserInput): The updated user data.
        db (Session): The database session.

    Returns:
        UserOutput: The updated user.
    """
    user_service = UserService(db)
    return user_service.update_user(user_id, user_update)

@router.delete("/{user_id}", response_model=bool)
def delete_user(user_id: UUID, db: Session = Depends(get_db)) -> bool:
    """
    Delete a user.

    Args:
        user_id (UUID): The ID of the user to delete.
        db (Session): The database session.

    Returns:
        bool: True if the user was successfully deleted, False otherwise.
    """
    user_service = UserService(db)
    return user_service.delete_user(user_id)

@router.get("/", response_model=List[UserOutput])
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)) -> List[UserOutput]:
    """
    List users with pagination.

    Args:
        skip (int, optional): The number of users to skip. Defaults to 0.
        limit (int, optional): The maximum number of users to return. Defaults to 100.
        db (Session): The database session.

    Returns:
        List[UserOutput]: A list of users.
    """
    user_service = UserService(db)
    return user_service.list_users(skip, limit)

@router.post("/{user_id}/teams/{team_id}", response_model=bool)
def add_user_to_team(user_id: UUID, team_id: UUID, db: Session = Depends(get_db)) -> bool:
    """
    Add a user to a team.

    Args:
        user_id (UUID): The ID of the user to add to the team.
        team_id (UUID): The ID of the team to add the user to.
        db (Session): The database session.

    Returns:
        bool: True if the user was successfully added to the team, False otherwise.
    """
    user_service = UserService(db)
    return user_service.add_user_to_team(user_id, team_id)

@router.delete("/{user_id}/teams/{team_id}", response_model=bool)
def remove_user_from_team(user_id: UUID, team_id: UUID, db: Session = Depends(get_db)) -> bool:
    """
    Remove a user from a team.

    Args:
        user_id (UUID): The ID of the user to remove from the team.
        team_id (UUID): The ID of the team to remove the user from.
        db (Session): The database session.

    Returns:
        bool: True if the user was successfully removed from the team, False otherwise.
    """
    user_service = UserService(db)
    return user_service.remove_user_from_team(user_id, team_id)