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
    user_service = UserService(db)
    return user_service.create_user(user)

@router.get("/{user_id}", response_model=UserOutput)
def get_user(user_id: UUID, db: Session = Depends(get_db)) -> UserOutput:
    user_service = UserService(db)
    return user_service.get_user_by_id(user_id)

@router.put("/{user_id}", response_model=UserOutput)
def update_user(user_id: UUID, user_update: UserInput, db: Session = Depends(get_db)) -> UserOutput:
    user_service = UserService(db)
    return user_service.update_user(user_id, user_update)

@router.delete("/{user_id}", response_model=bool)
def delete_user(user_id: UUID, db: Session = Depends(get_db)) -> bool:
    user_service = UserService(db)
    return user_service.delete_user(user_id)

@router.get("/", response_model=List[UserOutput])
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)) -> List[UserOutput]:
    user_service = UserService(db)
    return user_service.list_users(skip, limit)

@router.post("/{user_id}/teams/{team_id}", response_model=bool)
def add_user_to_team(user_id: UUID, team_id: UUID, db: Session = Depends(get_db)) -> bool:
    user_service = UserService(db)
    return user_service.add_user_to_team(user_id, team_id)

@router.delete("/{user_id}/teams/{team_id}", response_model=bool)
def remove_user_from_team(user_id: UUID, team_id: UUID, db: Session = Depends(get_db)) -> bool:
    user_service = UserService(db)
    return user_service.remove_user_from_team(user_id, team_id)
