"""Common dependencies for FastAPI routes.

This module provides reusable dependencies for authentication, authorization,
and service injection that can be used across all routers.
"""

from typing import Optional
from uuid import UUID

from fastapi import Depends, Request, HTTPException
from sqlalchemy.orm import Session

from rag_solution.file_management.database import get_db
from rag_solution.services.user_service import UserService
from rag_solution.schemas.user_schema import UserOutput
from rag_solution.core.exceptions import NotFoundError, InsufficientPermissionsError


def get_current_user(request: Request) -> dict:
    """Extract current user from request state.
    
    This assumes authentication middleware has already validated the user
    and added user info to request.state.
    """
    if not hasattr(request.state, "user"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return request.state.user


def verify_user_access(
    user_id: UUID,
    request: Request,
    db: Session = Depends(get_db)
) -> UserOutput:
    """Verify that the current user has access to the requested user resource.
    
    Args:
        user_id: The user ID being accessed
        request: The FastAPI request object
        db: Database session
        
    Returns:
        UserOutput object if access is granted
        
    Raises:
        HTTPException: 401 if not authenticated, 403 if not authorized
    """
    current_user = get_current_user(request)
    
    # Check if user is accessing their own resources
    if current_user["uuid"] != str(user_id):
        # Could add admin check here if needed
        raise HTTPException(status_code=403, detail="Not authorized to access this user's resources")
    
    # Get and return the user object
    try:
        user_service = UserService(db)
        return user_service.get_user_by_id(user_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


def verify_admin_access(request: Request) -> dict:
    """Verify that the current user has admin privileges.
    
    Args:
        request: The FastAPI request object
        
    Returns:
        Current user dict if admin
        
    Raises:
        HTTPException: 401 if not authenticated, 403 if not admin
    """
    current_user = get_current_user(request)
    
    # Check for admin role (adjust based on your auth system)
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return current_user


def verify_collection_access(
    collection_id: UUID,
    user_id: UUID,
    request: Request,
    db: Session = Depends(get_db)
) -> bool:
    """Verify that a user has access to a specific collection.
    
    Args:
        collection_id: The collection ID to check
        user_id: The user ID requesting access
        request: The FastAPI request object
        db: Database session
        
    Returns:
        True if access is granted
        
    Raises:
        HTTPException: 401 if not authenticated, 403 if not authorized
    """
    current_user = get_current_user(request)
    
    # Verify user is accessing their own resources
    if current_user["uuid"] != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Check collection ownership (implement based on your business logic)
    from rag_solution.services.user_collection_service import UserCollectionService
    user_collection_service = UserCollectionService(db)
    
    try:
        user_collections = user_collection_service.get_user_collections(user_id)
        if not any(uc.collection_id == collection_id for uc in user_collections):
            raise HTTPException(
                status_code=403,
                detail="You don't have access to this collection"
            )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    return True


def verify_team_access(
    team_id: UUID,
    user_id: UUID,
    request: Request,
    db: Session = Depends(get_db)
) -> bool:
    """Verify that a user has access to a specific team.
    
    Args:
        team_id: The team ID to check
        user_id: The user ID requesting access
        request: The FastAPI request object
        db: Database session
        
    Returns:
        True if access is granted
        
    Raises:
        HTTPException: 401 if not authenticated, 403 if not authorized
    """
    current_user = get_current_user(request)
    
    # Verify user is accessing their own resources
    if current_user["uuid"] != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Check team membership
    from rag_solution.services.user_team_service import UserTeamService
    user_team_service = UserTeamService(db)
    
    try:
        user_teams = user_team_service.get_user_teams(user_id)
        if not any(ut.team_id == team_id for ut in user_teams):
            raise HTTPException(
                status_code=403,
                detail="You are not a member of this team"
            )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Team not found")
    
    return True


# Service dependency factories
def get_user_service(db: Session = Depends(get_db)) -> UserService:
    """Get UserService instance."""
    return UserService(db)


def get_collection_service(db: Session = Depends(get_db)):
    """Get CollectionService instance."""
    from rag_solution.services.collection_service import CollectionService
    return CollectionService(db)


def get_file_service(db: Session = Depends(get_db)):
    """Get FileManagementService instance."""
    from rag_solution.services.file_management_service import FileManagementService
    return FileManagementService(db)


def get_team_service(db: Session = Depends(get_db)):
    """Get TeamService instance."""
    from rag_solution.services.team_service import TeamService
    return TeamService(db)


def get_pipeline_service(db: Session = Depends(get_db)):
    """Get PipelineService instance."""
    from rag_solution.services.pipeline_service import PipelineService
    return PipelineService(db)


def get_llm_provider_service(db: Session = Depends(get_db)):
    """Get LLMProviderService instance."""
    from rag_solution.services.llm_provider_service import LLMProviderService
    return LLMProviderService(db)