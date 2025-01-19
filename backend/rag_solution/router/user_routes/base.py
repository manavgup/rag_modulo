"""Core user routes."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from rag_solution.file_management.database import get_db
from rag_solution.schemas.user_schema import UserInput, UserOutput
from rag_solution.services.user_service import UserService
from core.authorization import authorize_decorator

import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/", 
    response_model=UserOutput,
    summary="Create new user",
    description="Create a new user with the provided details",
    responses={
        200: {"description": "User created successfully"},
        400: {"description": "Invalid input data"},
        403: {"description": "Not authorized"},
        500: {"description": "Internal server error"}
    }
)
@authorize_decorator(role="admin")
async def create_user(
    user_input: UserInput,
    request: Request,
    db: Session = Depends(get_db)
) -> UserOutput:
    """Create a new user."""
    service = UserService(db)
    try:
        return service.create_user(user_input)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to create user: {str(e)}"
        )

@router.get("/{user_id}", 
    response_model=UserOutput,
    summary="Get user details",
    description="Retrieve details for a specific user",
    responses={
        200: {"description": "User details retrieved successfully"},
        403: {"description": "Not authorized"},
        404: {"description": "User not found"},
        500: {"description": "Internal server error"}
    }
)
@authorize_decorator(role="user")
async def get_user(
    user_id: UUID,
    request: Request,
    db: Session = Depends(get_db)
) -> UserOutput:
    """Retrieve details for a specific user."""
    if not hasattr(request.state, 'user') or request.state.user['uuid'] != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized to access user details")
    
    service = UserService(db)
    try:
        return service.get_user(user_id)
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"User not found: {str(e)}"
        )

@router.put("/{user_id}", 
    response_model=UserOutput,
    summary="Update user details",
    description="Update details for a specific user",
    responses={
        200: {"description": "User details updated successfully"},
        400: {"description": "Invalid input data"},
        403: {"description": "Not authorized"},
        404: {"description": "User not found"},
        500: {"description": "Internal server error"}
    }
)
@authorize_decorator(role="user")
async def update_user(
    user_id: UUID,
    user_input: UserInput,
    request: Request,
    db: Session = Depends(get_db)
) -> UserOutput:
    """Update details for a specific user."""
    if not hasattr(request.state, 'user') or request.state.user['uuid'] != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized to update user details")
    
    service = UserService(db)
    try:
        return service.update_user(user_id, user_input)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to update user: {str(e)}"
        )

@router.delete("/{user_id}", 
    response_model=bool,
    summary="Delete user",
    description="Delete a specific user",
    responses={
        200: {"description": "User deleted successfully"},
        403: {"description": "Not authorized"},
        404: {"description": "User not found"},
        500: {"description": "Internal server error"}
    }
)
@authorize_decorator(role="user")
async def delete_user(
    user_id: UUID,
    request: Request,
    db: Session = Depends(get_db)
) -> bool:
    """Delete a specific user."""
    if not hasattr(request.state, 'user') or request.state.user['uuid'] != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized to delete user")
    
    service = UserService(db)
    try:
        return service.delete_user(user_id)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to delete user: {str(e)}"
        )
