from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from rag_solution.file_management.database import get_db
from rag_solution.services.user_team_service import UserTeamService
from rag_solution.schemas.user_team_schema import UserTeamOutput

router = APIRouter(prefix="/api/user-teams", tags=["user-teams"])

@router.post("/{user_id}/{team_id}", 
    response_model=bool,
    summary="Add user to team",
    description="Add a user to a specific team",
    responses={
        200: {"description": "User successfully added to team"},
        404: {"description": "User or team not found"},
        500: {"description": "Internal server error"}
    }
)
def add_user_to_team(user_id: UUID, team_id: UUID, db: Session = Depends(get_db)):
    service = UserTeamService(db)
    return service.add_user_to_team(user_id, team_id)

@router.delete("/{user_id}/{team_id}", 
    response_model=bool,
    summary="Remove user from team",
    description="Remove a user from a specific team",
    responses={
        200: {"description": "User successfully removed from team"},
        404: {"description": "User or team not found"},
        500: {"description": "Internal server error"}
    }
)
def remove_user_from_team(user_id: UUID, team_id: UUID, db: Session = Depends(get_db)):
    service = UserTeamService(db)
    return service.remove_user_from_team(user_id, team_id)

@router.get("/{user_id}", 
    response_model=List[UserTeamOutput],
    summary="Get user teams",
    description="Get all teams associated with a user",
    responses={
        200: {"description": "Successfully retrieved user teams"},
        404: {"description": "User not found"},
        500: {"description": "Internal server error"}
    }
)
def get_user_teams(user_id: UUID, db: Session = Depends(get_db)):
    service = UserTeamService(db)
    return service.get_user_teams(user_id)

@router.get("/team/{team_id}", 
    response_model=List[UserTeamOutput],
    summary="Get team users",
    description="Get all users associated with a team",
    responses={
        200: {"description": "Successfully retrieved team users"},
        404: {"description": "Team not found"},
        500: {"description": "Internal server error"}
    }
)
def get_team_users(team_id: UUID, db: Session = Depends(get_db)):
    service = UserTeamService(db)
    return service.get_team_users(team_id)