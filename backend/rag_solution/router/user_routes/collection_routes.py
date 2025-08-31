"""Collection routes for user-specific operations."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from rag_solution.core.dependencies import verify_user_access
from rag_solution.file_management.database import get_db
from rag_solution.schemas.collection_schema import CollectionOutput
from rag_solution.schemas.user_schema import UserOutput
from rag_solution.services.user_collection_service import UserCollectionService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/{user_id}/collections",
    response_model=list[CollectionOutput],
    summary="Get user collections",
    description="Retrieve all collections for a user",
    responses={
        200: {"description": "Collections retrieved successfully"},
        403: {"description": "Not authorized"},
        500: {"description": "Internal server error"},
    },
)
async def get_user_collections(
    user_id: UUID, db: Session = Depends(get_db), user: UserOutput = Depends(verify_user_access)
) -> list[CollectionOutput]:
    """Retrieve all collections for a user."""
    service = UserCollectionService(db)
    try:
        return service.get_user_collections(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve collections: {e!s}") from e


@router.delete(
    "/{user_id}/collections/{collection_id}",
    response_model=bool,
    summary="Remove collection from user",
    description="Remove a collection from a user's access",
    responses={
        200: {"description": "Collection removed successfully"},
        403: {"description": "Not authorized"},
        404: {"description": "Collection not found"},
        500: {"description": "Internal server error"},
    },
)
async def remove_user_collection(
    user_id: UUID, collection_id: UUID, db: Session = Depends(get_db), user: UserOutput = Depends(verify_user_access)
) -> bool:
    """Remove a collection from a user's access."""
    service = UserCollectionService(db)
    try:
        return service.remove_user_from_collection(user_id, collection_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to remove collection: {e!s}") from e
