from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.rag_solution.file_management.database import get_db
from backend.rag_solution.schemas.team_schema import TeamInput, TeamOutput
from backend.rag_solution.services.team_service import TeamService

router = APIRouter()

def get_team_service(db: Session = Depends(get_db)) -> TeamService:
    return TeamService(db)

@router.post("/", response_model=TeamOutput)
def create_team(team: TeamInput, db: Session = Depends(get_db)) -> TeamOutput:
    team_service = get_team_service(db)
    try:
        return team_service.create_team(team)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/{team_id}", response_model=TeamOutput)
def get_team(team_id: UUID, db: Session = Depends(get_db)) -> TeamOutput:
    team_service = get_team_service(db)
    team = team_service.get_team_by_id(team_id)
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    return team

@router.put("/{team_id}", response_model=TeamOutput)
def update_team(team_id: UUID, team_update: TeamInput, db: Session = Depends(get_db)) -> TeamOutput:
    team_service = get_team_service(db)
    team = team_service.update_team(team_id, team_update)
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    return team

@router.delete("/{team_id}", response_model=bool)
def delete_team(team_id: UUID, db: Session = Depends(get_db)) -> bool:
    team_service = get_team_service(db)
    return team_service.delete_team(team_id)

@router.get("/", response_model=List[TeamOutput])
def list_teams(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)) -> List[TeamOutput]:
    team_service = get_team_service(db)
    return team_service.list_teams(skip, limit)
