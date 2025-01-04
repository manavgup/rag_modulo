from typing import List, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from rag_solution.file_management.database import get_db
from rag_solution.schemas.user_schema import UserInput, UserOutput
from rag_solution.services.user_service import UserService
from rag_solution.services.user_collection_service import UserCollectionService
from rag_solution.services.runtime_config_service import RuntimeConfigService
from rag_solution.schemas.provider_config_schema import ProviderConfig
from rag_solution.services.user_collection_interaction_service import UserCollectionInteractionService
from rag_solution.services.file_management_service import FileManagementService
from rag_solution.schemas.user_collection_schema import UserCollectionOutput, UserCollectionsOutput
from rag_solution.schemas.file_schema import DocumentDelete, FileOutput, FileMetadata
from rag_solution.services.user_team_service import UserTeamService
from rag_solution.schemas.user_team_schema import UserTeamOutput

from core.authorization import authorize_decorator

import logging

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["users"])

@router.get("", 
    response_model=List[UserOutput],
    summary="List all users",
    description="Retrieve a list of all users with pagination",
    responses={
        200: {"description": "Users retrieved successfully"},
        500: {"description": "Internal server error"}
    }
)
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)) -> List[UserOutput]:
    """
    List users with pagination.

    Args:
        skip (int, optional): The number of users to skip. Defaults to 0.
        limit (int, optional): The maximum number of users to return. Defaults to 100.
        db (Session): The database session.

    Returns:
        List[UserOutput]: A list of users.
    """
    user_service = UserService(db)
    return user_service.list_users(skip, limit)

@router.post("", 
    response_model=UserOutput,
    summary="Create a new user",
    description="Create a new user with the provided input data",
    responses={
        201: {"description": "User created successfully"},
        400: {"description": "Invalid input data"},
        500: {"description": "Internal server error"}
    }
)
def create_user(user: UserInput, db: Session = Depends(get_db)) -> UserOutput:
    """
    Create a new user.

    Args:
        user (UserInput): The input data for creating a user.
        db (Session): The database session.

    Returns:
        UserOutput: The created user.
    """
    user_service = UserService(db)
    return user_service.create_user(user)

@router.get("/{user_id}", 
    response_model=UserOutput,
    summary="Get a user by ID",
    description="Retrieve a user's information using their unique identifier",
    responses={
        200: {"description": "User retrieved successfully"},
        404: {"description": "User not found"},
        500: {"description": "Internal server error"}
    }
)
def get_user(user_id: UUID, db: Session = Depends(get_db)) -> UserOutput:
    """
    Get a user by their ID.

    Args:
        user_id (UUID): The ID of the user to retrieve.
        db (Session): The database session.

    Returns:
        UserOutput: The retrieved user.
    """
    user_service = UserService(db)
    return user_service.get_user_by_id(user_id)

@router.put("/{user_id}", 
    response_model=UserOutput,
    summary="Update a user",
    description="Update an existing user's information",
    responses={
        200: {"description": "User updated successfully"},
        404: {"description": "User not found"},
        400: {"description": "Invalid input data"},
        500: {"description": "Internal server error"}
    }
)
def update_user(user_id: UUID, user_update: UserInput, db: Session = Depends(get_db)) -> UserOutput:
    """
    Update a user.

    Args:
        user_id (UUID): The ID of the user to update.
        user_update (UserInput): The updated user data.
        db (Session): The database session.

    Returns:
        UserOutput: The updated user.
    """
    user_service = UserService(db)
    return user_service.update_user(user_id, user_update)

@router.delete("/{user_id}", 
    response_model=bool,
    summary="Delete a user",
    description="Delete a user using their unique identifier",
    responses={
        200: {"description": "User deleted successfully"},
        404: {"description": "User not found"},
        500: {"description": "Internal server error"}
    }
)
def delete_user(user_id: UUID, db: Session = Depends(get_db)) -> bool:
    """
    Delete a user.

    Args:
        user_id (UUID): The ID of the user to delete.
        db (Session): The database session.

    Returns:
        bool: True if the user was successfully deleted, False otherwise.
    """
    user_service = UserService(db)
    return user_service.delete_user(user_id)

@router.get("/{user_id}/collections", 
    response_model=UserCollectionsOutput,
    summary="Get user collections",
    description="Get all collections associated with a user",
    responses={
        200: {"description": "Successfully retrieved user collections"},
        404: {"description": "User not found"},
        500: {"description": "Internal server error"}
    }
)

@authorize_decorator(role="admin")
async def get_user_collections(user_id: UUID, request: Request, db: Session = Depends(get_db)):
    if not hasattr(request.state, 'user') or request.state.user['uuid'] != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized to access this resource")
    
    service = UserCollectionInteractionService(db)
    try:
        collections = service.get_user_collections_with_files(user_id)
        return collections
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching user collections: {str(e)}"
        )

@router.post("/{user_id}/collections/{collection_id}", 
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

@router.delete("/{user_id}/collections/{collection_id}", 
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

@router.post("/{user_id}/collections/{collection_id}/files", 
    response_model=FileOutput,
    summary="Upload a file",
    description="Upload a file to a specific collection for a user",
    responses={
        200: {"description": "File uploaded successfully"},
        400: {"description": "Invalid input"},
        404: {"description": "User or collection not found"},
        500: {"description": "Internal server error"}
    }
)
def upload_file(user_id: UUID, collection_id: UUID, file: UploadFile, metadata: Optional[FileMetadata] = None, db: Session = Depends(get_db)):
    """
    Upload a file to a specific collection for a user.

    Args:
        user_id (UUID): The ID of the user uploading the file.
        collection_id (UUID): The ID of the collection to upload the file to.
        file (UploadFile): The file to be uploaded.
        db (Session): The database session.

    Returns:
        FileOutput: The uploaded file information.
    """
    _file_service = FileManagementService(db)
    return _file_service.upload_and_create_file_record(file, user_id, collection_id, metadata)

@router.get("/{user_id}/teams", 
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

@router.post("/{user_id}/teams/{team_id}", 
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

@router.delete("/{user_id}/teams/{team_id}", 
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

@router.get("/{user_id}/provider-preference",
    response_model=ProviderConfig,
    summary="Get user's provider preference",
    description="Get the user's preferred LLM provider configuration",
    responses={
        200: {"description": "Successfully retrieved provider preference"},
        404: {"description": "No preference found"},
        500: {"description": "Internal server error"}
    }
)
@authorize_decorator(role="user")
async def get_provider_preference(
    user_id: UUID,
    request: Request,
    db: Session = Depends(get_db)
):
    """Get user's preferred provider configuration."""
    if not hasattr(request.state, 'user') or request.state.user['uuid'] != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized to access this resource")
    
    service = RuntimeConfigService(db)
    try:
        config = await service.get_runtime_config(user_id)
        return config.provider_config
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"No provider preference found: {str(e)}"
        )

@router.post("/{user_id}/provider-preference/{config_id}",
    response_model=ProviderConfig,
    summary="Set user's provider preference",
    description="Set the user's preferred LLM provider configuration",
    responses={
        200: {"description": "Successfully set provider preference"},
        404: {"description": "Provider config not found"},
        500: {"description": "Internal server error"}
    }
)
@authorize_decorator(role="user")
async def set_provider_preference(
    user_id: UUID,
    config_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Set user's preferred provider configuration."""
    if not hasattr(request.state, 'user') or request.state.user['uuid'] != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized to access this resource")
    
    service = RuntimeConfigService(db)
    try:
        await service.set_user_provider_preference(user_id, config_id)
        config = await service.get_runtime_config(user_id)
        return config.provider_config
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to set provider preference: {str(e)}"
        )

@router.delete("/{user_id}/provider-preference",
    summary="Clear user's provider preference",
    description="Remove the user's preferred LLM provider configuration",
    responses={
        200: {"description": "Successfully cleared provider preference"},
        500: {"description": "Internal server error"}
    }
)
@authorize_decorator(role="user")
async def clear_provider_preference(
    user_id: UUID,
    request: Request,
    db: Session = Depends(get_db)
):
    """Clear user's provider preference."""
    if not hasattr(request.state, 'user') or request.state.user['uuid'] != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized to access this resource")
    
    service = RuntimeConfigService(db)
    try:
        await service.clear_user_provider_preference(user_id)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear provider preference: {str(e)}"
        )
