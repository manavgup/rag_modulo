from fastapi import APIRouter, Depends, HTTPException
from typing import List
from uuid import UUID

from backend.rag_solution.services.team_service import TeamService, get_team_service
from backend.rag_solution.schemas.team_schema import TeamInput, TeamOutput, TeamUpdateSchema, UserTeamInDB

router = APIRouter(prefix="/teams", tags=["teams"])

@router.post("/", response_model=TeamOutput)
async def create_team(team: TeamInput, team_service: TeamService = Depends(get_team_service)):
    return team_service.create_team(team)

@router.get("/{team_id}", response_model=TeamOutput)
async def get_team(team_id: UUID, team_service: TeamService = Depends(get_team_service)):
    team = team_service.get_team(team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")
    return team

@router.put("/{team_id}", response_model=TeamOutput)
async def update_team(team_id: UUID, team_update: TeamUpdateSchema, team_service: TeamService = Depends(get_team_service)):
    updated_team = team_service.update_team(team_id, team_update)
    if updated_team is None:
        raise HTTPException(status_code=404, detail="Team not found")
    return updated_team

@router.delete("/{team_id}")
async def delete_team(team_id: UUID, team_service: TeamService = Depends(get_team_service)):
    if not team_service.delete_team(team_id):
        raise HTTPException(status_code=404, detail="Team not found")
    return {"message": "Team deleted successfully"}

@router.post("/{team_id}/users/{user_id}", response_model=UserTeamInDB)
async def add_user_to_team(team_id: UUID, user_id: UUID, team_service: TeamService = Depends(get_team_service)):
    user_team = team_service.add_user_to_team(user_id, team_id)
    if user_team is None:
        raise HTTPException(status_code=400, detail="Failed to add user to team")
    return user_team

@router.delete("/{team_id}/users/{user_id}")
async def remove_user_from_team(team_id: UUID, user_id: UUID, team_service: TeamService = Depends(get_team_service)):
    if not team_service.remove_user_from_team(user_id, team_id):
        raise HTTPException(status_code=404, detail="User not found in team")
    return {"message": "User removed from team successfully"}

@router.get("/{team_id}/users", response_model=List[UserTeamInDB])
async def get_team_users(team_id: UUID, team_service: TeamService = Depends(get_team_service)):
    return team_service.get_team_users(team_id)
