"""Collection routes for user-specific operations."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from core.authorization import authorize_decorator
from rag_solution.file_management.database import get_db
from rag_solution.schemas.collection_schema import CollectionOutput
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
@authorize_decorator(role="user")
async def get_user_collections(
    user_id: UUID, request: Request, db: Session = Depends(get_db), include_system: bool = Query(True)
) -> list[CollectionOutput]:
    """Retrieve all collections for a user."""
    if not hasattr(request.state, "user") or request.state.user["uuid"] != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized to access collections")

    service = UserCollectionService(db)
    try:
        return service.get_user_collections(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve collections: {e!s}")


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
@authorize_decorator(role="user")
async def remove_user_collection(
    user_id: UUID, collection_id: UUID, request: Request, db: Session = Depends(get_db)
) -> bool:
    """Remove a collection from a user's access."""
    if not hasattr(request.state, "user") or request.state.user["uuid"] != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized to remove collection")

    service = UserCollectionService(db)
    try:
        return service.remove_user_from_collection(user_id, collection_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to remove collection: {e!s}")
