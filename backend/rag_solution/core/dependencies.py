"""Common dependencies for FastAPI routes.

This module provides reusable dependencies for authentication, authorization,
and service injection that can be used across all routers.
"""

import logging
from typing import Any
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from pydantic import UUID4
from sqlalchemy.orm import Session

from core.config import Settings, get_settings
from rag_solution.core.exceptions import NotFoundError
from rag_solution.file_management.database import get_db
from rag_solution.schemas.user_schema import UserOutput
from rag_solution.services.collection_service import CollectionService
from rag_solution.services.file_management_service import FileManagementService
from rag_solution.services.llm_parameters_service import LLMParametersService
from rag_solution.services.llm_provider_service import LLMProviderService
from rag_solution.services.pipeline_service import PipelineService
from rag_solution.services.question_service import QuestionService
from rag_solution.services.search_service import SearchService
from rag_solution.services.team_service import TeamService
from rag_solution.services.user_collection_service import UserCollectionService
from rag_solution.services.user_service import UserService
from rag_solution.services.user_team_service import UserTeamService

logger = logging.getLogger(__name__)


def get_current_user(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> dict[Any, Any]:
    """Extract current user from request state.

    This assumes authentication middleware has already validated the user
    and added user info to request.state.

    In development mode with SKIP_AUTH=true, returns a mock user.
    Returns user_id as UUID object for consistency with database models.
    """
    # Check if authentication is skipped (development mode)
    if settings.skip_auth:
        # In bypass mode, user should be set by authentication middleware
        # This is a fallback that should rarely be used
        if hasattr(request.state, "user"):
            user_data = request.state.user.copy()  # Create copy to avoid mutating original

            # Apply the same user_id mapping logic as production mode
            if "user_id" not in user_data and "uuid" in user_data:
                user_data["user_id"] = (
                    UUID(user_data["uuid"]) if isinstance(user_data["uuid"], str) else user_data["uuid"]
                )
            elif isinstance(user_data.get("user_id"), str):
                user_data["user_id"] = UUID(user_data["user_id"])

            return user_data

        # Final fallback - should not happen in normal flow
        logger.warning("SKIP_AUTH=true but no user in request.state - using fallback")
        from core.identity_service import IdentityService

        mock_uuid = str(IdentityService.get_mock_user_id())
        return {
            "user_id": mock_uuid,
            "uuid": mock_uuid,
            "email": settings.mock_user_email,
            "name": settings.mock_user_name,
            "role": "admin",
        }

    # Production: require authentication
    if not hasattr(request.state, "user"):
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_data = request.state.user.copy()  # Create copy to avoid mutating original

    # TODO: Standardize on single UUID field name (either 'user_id' or 'uuid') throughout codebase
    # Current dual-field pattern adds type conversion overhead and potential confusion
    # Tracked in follow-up issue for codebase-wide standardization

    # Ensure user_id is set as UUID object (some code expects it alongside uuid)
    if "user_id" not in user_data and "uuid" in user_data:
        # Convert string UUID to UUID object for consistency with database
        user_data["user_id"] = UUID(user_data["uuid"]) if isinstance(user_data["uuid"], str) else user_data["uuid"]
    elif isinstance(user_data.get("user_id"), str):
        user_data["user_id"] = UUID(user_data["user_id"])

    return user_data  # type: ignore[no-any-return]


def verify_user_access(
    user_id: UUID4, request: Request, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> UserOutput:
    """Verify that the current user has access to the requested user resource.

    Args:
        user_id: The user ID being accessed
        request: The FastAPI request object
        db: Session
        settings: Application settings

    Returns:
        UserOutput object if access is granted

    Raises:
        HTTPException: 401 if not authenticated, 403 if not authorized
    """
    current_user = get_current_user(request, settings)

    # Check if user is accessing their own resources
    current_user_id = current_user.get("uuid")
    if current_user_id != str(user_id):
        # Could add admin check here if needed
        raise HTTPException(status_code=403, detail="Not authorized to access this user's resources")

    # Get and return the user object
    try:
        user_service = UserService(db, settings)
        return user_service.get_user_by_id(user_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


def verify_admin_access(
    request: Request, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> UserOutput:
    """Verify that the current user has admin privileges.

    Args:
        request: The FastAPI request object
        db: Database session
        settings: Application settings

    Returns:
        Current user if admin

    Raises:
        HTTPException: 401 if not authenticated, 403 if not admin
    """
    current_user_data = get_current_user(request, settings)

    # Get the full user object to check role
    try:
        user_service = UserService(db, settings)
        user_id = UUID4(current_user_data.get("uuid"))
        current_user = user_service.get_user_by_id(user_id)
    except (ValueError, NotFoundError) as e:
        raise HTTPException(status_code=401, detail="Invalid user") from e

    # Check for admin role
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    return current_user


def verify_collection_access(
    collection_id: UUID4,
    user_id: UUID4,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> bool:
    """Verify that a user has access to a specific collection.

    Args:
        collection_id: The collection ID to check
        user_id: The user ID requesting access
        request: The FastAPI request object
        db: Database session
        settings: Application settings

    Returns:
        True if access is granted

    Raises:
        HTTPException: 401 if not authenticated, 403 if not authorized
    """
    current_user = get_current_user(request, settings)

    # Verify user is accessing their own resources
    current_user_id = current_user.get("uuid")
    if current_user_id != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    # Check collection ownership (implement based on your business logic)
    user_collection_service = UserCollectionService(db)

    try:
        user_collections = user_collection_service.get_user_collections(user_id)
        if not any(uc.id == collection_id for uc in user_collections):
            raise HTTPException(status_code=403, detail="You don't have access to this collection")
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Collection not found") from None

    return True


def verify_team_access(
    team_id: UUID4,
    user_id: UUID4,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> bool:
    """Verify that a user has access to a specific team.

    Args:
        team_id: The team ID to check
        user_id: The user ID requesting access
        request: The FastAPI request object
        db: Database session
        settings: Application settings

    Returns:
        True if access is granted

    Raises:
        HTTPException: 401 if not authenticated, 403 if not authorized
    """
    current_user = get_current_user(request, settings)

    # Verify user is accessing their own resources
    current_user_id = current_user.get("uuid")
    if current_user_id != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    # Check team membership
    user_team_service = UserTeamService(db)

    try:
        user_teams = user_team_service.get_user_teams(user_id)
        if not any(ut.team_id == team_id for ut in user_teams):
            raise HTTPException(status_code=403, detail="You are not a member of this team")
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Team not found") from None

    return True


# Service dependency factories
def get_user_service(db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> UserService:
    """Get UserService instance."""
    return UserService(db, settings)


def get_collection_service(
    db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> CollectionService:
    """Get CollectionService instance with proper dependency injection."""
    return CollectionService(db, settings)


def get_file_service(
    db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> FileManagementService:
    """Get FileManagementService instance with proper dependency injection."""
    return FileManagementService(db, settings)


def get_team_service(db: Session = Depends(get_db)) -> TeamService:
    """Get TeamService instance."""
    return TeamService(db)


def get_pipeline_service(db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> PipelineService:
    """Get PipelineService instance with proper dependency injection."""
    return PipelineService(db, settings)


def get_llm_provider_service(
    db: Session = Depends(get_db), _settings: Settings = Depends(get_settings)
) -> LLMProviderService:
    """Get LLMProviderService instance."""
    return LLMProviderService(db)


def get_question_service(db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> QuestionService:
    """Get QuestionService instance with proper dependency injection."""
    return QuestionService(db, settings)


def get_search_service(db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> SearchService:
    """Get SearchService instance with proper dependency injection."""
    return SearchService(db, settings)


def get_llm_parameters_service(
    db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> LLMParametersService:
    """Get LLMParametersService instance with proper dependency injection."""
    return LLMParametersService(db, settings)
