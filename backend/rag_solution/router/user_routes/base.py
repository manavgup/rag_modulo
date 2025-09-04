"""Core user routes."""

import logging
from pydantic import UUID4

from fastapi import APIRouter, Depends, HTTPException

from core.authorization import authorize_decorator
from rag_solution.core.dependencies import get_user_service, verify_user_access
from rag_solution.core.exceptions import AlreadyExistsError, NotFoundError, ValidationError
from rag_solution.schemas.user_schema import UserInput, UserOutput
from rag_solution.services.user_service import UserService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/",
    response_model=UserOutput,
    summary="Create new user",
    description="Create a new user with the provided details",
    responses={
        200: {"description": "User created successfully"},
        400: {"description": "Invalid input data"},
        403: {"description": "Not authorized"},
        500: {"description": "Internal server error"},
    },
)
@authorize_decorator(role="admin")
async def create_user(
    user_input: UserInput,
    service: UserService = Depends(get_user_service)
) -> UserOutput:
    """Create a new user."""
    try:
        return service.create_user(user_input)
    except AlreadyExistsError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get(
    "/{user_id}",
    response_model=UserOutput,
    summary="Get user details",
    description="Retrieve details for a specific user",
    responses={
        200: {"description": "User details retrieved successfully"},
        403: {"description": "Not authorized"},
        404: {"description": "User not found"},
        500: {"description": "Internal server error"},
    },
)
@authorize_decorator(role="user")
async def get_user(
    user_id: UUID4,
    user: UserOutput = Depends(verify_user_access)
) -> UserOutput:
    """Retrieve details for a specific user."""
    # User access is already verified by dependency
    return user


@router.put(
    "/{user_id}",
    response_model=UserOutput,
    summary="Update user details",
    description="Update details for a specific user",
    responses={
        200: {"description": "User details updated successfully"},
        400: {"description": "Invalid input data"},
        403: {"description": "Not authorized"},
        404: {"description": "User not found"},
        500: {"description": "Internal server error"},
    },
)
@authorize_decorator(role="user")
async def update_user(
    user_id: UUID4,
    user_input: UserInput,
    user: UserOutput = Depends(verify_user_access),
    service: UserService = Depends(get_user_service)
) -> UserOutput:
    """Update details for a specific user."""
    try:
        return service.update_user(user_id, user_input)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except AlreadyExistsError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete(
    "/{user_id}",
    response_model=dict,
    summary="Delete user",
    description="Delete a specific user",
    responses={
        200: {"description": "User deleted successfully"},
        403: {"description": "Not authorized"},
        404: {"description": "User not found"},
        500: {"description": "Internal server error"},
    },
)
@authorize_decorator(role="user")
async def delete_user(
    user_id: UUID4,
    user: UserOutput = Depends(verify_user_access),
    service: UserService = Depends(get_user_service)
) -> dict:
    """Delete a specific user."""
    try:
        service.delete_user(user_id)
        return {"message": "User deleted successfully"}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
