from fastapi import APIRouter, Depends, HTTPException
from typing import List
from uuid import UUID

from backend.rag_solution.services.user_service import UserService, get_user_service
from backend.rag_solution.schemas.user_schema import UserInput, UserOutput, UserInDB
from backend.rag_solution.schemas.team_schema import TeamOutput

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", response_model=UserInDB)
async def create_user(user: UserInput, user_service: UserService = Depends(get_user_service)):
    """
    Create a new user.
    """
    return user_service.create_user(user)

@router.get("/{user_id}", response_model=UserOutput)
async def get_user(user_id: UUID, user_service: UserService = Depends(get_user_service)):
    """
    Get a user by their ID.
    """
    user = user_service.get_user(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.get("/ibm/{ibm_id}", response_model=UserOutput)
async def get_user_by_ibm_id(ibm_id: str, user_service: UserService = Depends(get_user_service)):
    """
    Get a user by their IBM ID.
    """
    user = user_service.get_user_by_ibm_id(ibm_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/{user_id}", response_model=UserOutput)
async def update_user(user_id: UUID, user_update: UserInput, user_service: UserService = Depends(get_user_service)):
    """
    Update a user's information.
    """
    updated_user = user_service.update_user(user_id, user_update)
    if updated_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return updated_user

@router.delete("/{user_id}")
async def delete_user(user_id: UUID, user_service: UserService = Depends(get_user_service)):
    """
    Delete a user.
    """
    if not user_service.delete_user(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}

@router.get("/{user_id}/teams", response_model=List[TeamOutput])
async def get_user_teams(user_id: UUID, user_service: UserService = Depends(get_user_service)):
    """
    Get all teams a user belongs to.
    """
    teams = user_service.get_user_teams(user_id)
    if not teams:
        raise HTTPException(status_code=404, detail="No teams found for this user")
    return teams
