from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from backend.rag_solution.file_management.database import get_db
from backend.rag_solution.services.user_collection_service import UserCollectionService
from backend.rag_solution.schemas.user_collection_schema import UserCollectionOutput

router = APIRouter(prefix="/api/user-collections", tags=["user-collections"])

@router.post("/{user_id}/{collection_id}", 
    response_model=bool,
    summary="Add user to collection",
    description="Add a user to a specific collection",
    responses={
        200: {"description": "User successfully added to collection"},
        404: {"description": "User or collection not found"},
        500: {"description": "Internal server error"}
    }
)
def add_user_to_collection(user_id: UUID, collection_id: UUID, db: Session = Depends(get_db)):
    service = UserCollectionService(db)
    return service.add_user_to_collection(user_id, collection_id)

@router.delete("/{user_id}/{collection_id}", 
    response_model=bool,
    summary="Remove user from collection",
    description="Remove a user from a specific collection",
    responses={
        200: {"description": "User successfully removed from collection"},
        404: {"description": "User or collection not found"},
        500: {"description": "Internal server error"}
    }
)
def remove_user_from_collection(user_id: UUID, collection_id: UUID, db: Session = Depends(get_db)):
    service = UserCollectionService(db)
    return service.remove_user_from_collection(user_id, collection_id)

@router.get("/{user_id}", 
    response_model=List[UserCollectionOutput],
    summary="Get user collections",
    description="Get all collections associated with a user",
    responses={
        200: {"description": "Successfully retrieved user collections"},
        404: {"description": "User not found"},
        500: {"description": "Internal server error"}
    }
)
def get_user_collections(user_id: UUID, db: Session = Depends(get_db)):
    service = UserCollectionService(db)
    try:
        collections = service.get_user_collections(user_id)
        if not collections:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No collections found for user with id {user_id}"
            )
        return collections
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching user collections: {str(e)}"
        )

@router.get("/collection/{collection_id}", 
    response_model=List[UserCollectionOutput],
    summary="Get collection users",
    description="Get all users associated with a collection",
    responses={
        200: {"description": "Successfully retrieved collection users"},
        404: {"description": "Collection not found"},
        500: {"description": "Internal server error"}
    }
)
def get_collection_users(collection_id: UUID, db: Session = Depends(get_db)):
    service = UserCollectionService(db)
    return service.get_collection_users(collection_id)