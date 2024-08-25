from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.rag_solution.file_management.database import get_db
from backend.rag_solution.schemas.user_schema import UserInput, UserOutput
from backend.rag_solution.services.user_service import UserService

router = APIRouter()

@router.post("/", 
    response_model=UserOutput,
    summary="Create a new user",
    description="Create a new user with the provided input data",
    responses={
        201: {"description": "User created successfully"},
        400: {"description": "Invalid input data"},
        500: {"description": "Internal server error"}
    }
)
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

@router.get("/{user_id}", 
    response_model=UserOutput,
    summary="Get a user by ID",
    description="Retrieve a user's information using their unique identifier",
    responses={
        200: {"description": "User retrieved successfully"},
        404: {"description": "User not found"},
        500: {"description": "Internal server error"}
    }
)
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

@router.put("/{user_id}", 
    response_model=UserOutput,
    summary="Update a user",
    description="Update an existing user's information",
    responses={
        200: {"description": "User updated successfully"},
        404: {"description": "User not found"},
        400: {"description": "Invalid input data"},
        500: {"description": "Internal server error"}
    }
)
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

@router.delete("/{user_id}", 
    response_model=bool,
    summary="Delete a user",
    description="Delete a user using their unique identifier",
    responses={
        200: {"description": "User deleted successfully"},
        404: {"description": "User not found"},
        500: {"description": "Internal server error"}
    }
)
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

@router.get("/", 
    response_model=List[UserOutput],
    summary="List all users",
    description="Retrieve a list of all users with pagination",
    responses={
        200: {"description": "Users retrieved successfully"},
        500: {"description": "Internal server error"}
    }
)
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
