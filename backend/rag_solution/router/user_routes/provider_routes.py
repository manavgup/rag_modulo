from fastapi import APIRouter, Depends
from pydantic import UUID4
from sqlalchemy.orm import Session

from rag_solution.file_management.database import get_db  # ✅ Import the session dependency
from rag_solution.schemas.user_schema import UserOutput
from rag_solution.services.user_service import UserService

router = APIRouter()


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    """Provides an instance of UserService with a database session."""
    return UserService(db)


@router.put("/{user_id}/preferred/{provider_id}", response_model=UserOutput)
def set_user_preferred_provider(
    user_id: UUID4,
    provider_id: UUID4,
    service: UserService = Depends(get_user_service),  # ✅ Provide the session via dependency injection
) -> UserOutput:
    """Sets the user's preferred LLM provider."""
    return service.set_user_preferred_provider(user_id, provider_id)


@router.get("/{user_id}/preferred", response_model=UserOutput)
def get_user_preferred_provider(
    user_id: UUID4,
    service: UserService = Depends(get_user_service),  # ✅ Provide the session via dependency injection
) -> UserOutput:
    """Retrieves the user's preferred LLM provider."""
    return service.get_user_by_id(user_id)
