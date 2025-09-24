"""Token warning router for token usage monitoring and warning management."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from core.config import Settings, get_settings
from rag_solution.file_management.database import get_db
from rag_solution.schemas.llm_usage_schema import TokenUsageStats
from rag_solution.services.token_tracking_service import TokenTrackingService

router = APIRouter(prefix="/api/token-warnings", tags=["token-warnings"])


def get_token_tracking_service(
    db: Annotated[Session, Depends(get_db)], settings: Annotated[Settings, Depends(get_settings)]
) -> TokenTrackingService:
    """
    Dependency to create a new TokenTrackingService instance.

    Args:
        db: Database session from dependency injection
        settings: Application settings from dependency injection

    Returns:
        TokenTrackingService: Initialized token tracking service instance
    """
    return TokenTrackingService(db, settings)


@router.get(
    "/user/{user_id}",
    summary="Get token warnings for a user",
    description="Retrieve token usage warnings for a specific user",
    responses={
        200: {"description": "Token warnings retrieved successfully"},
        404: {"description": "User not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_user_warnings(
    user_id: UUID,
    token_service: Annotated[TokenTrackingService, Depends(get_token_tracking_service)],
    acknowledged: bool | None = Query(None, description="Filter by acknowledgment status"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of warnings to return"),
    offset: int = Query(0, ge=0, description="Number of warnings to skip"),
) -> dict:
    """
    Get token warnings for a specific user.

    Args:
        user_id: User ID to get warnings for
        acknowledged: Filter by acknowledgment status (None for all)
        limit: Maximum number of warnings to return
        offset: Offset for pagination
        token_service: Token warning service instance

    Returns:
        Dictionary containing warnings and metadata
    """
    try:
        warnings = await token_service.get_user_warnings(user_id, acknowledged, limit, offset)
        return {
            "warnings": warnings,
            "total": len(warnings),
            "acknowledged_filter": acknowledged,
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving token warnings: {e!s}",
        ) from e


@router.get(
    "/user/{user_id}/stats",
    response_model=TokenUsageStats,
    summary="Get token usage statistics for a user",
    description="Retrieve aggregated token usage statistics for a specific user",
    responses={
        200: {"description": "Token usage statistics retrieved successfully"},
        404: {"description": "User not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_user_token_stats(
    user_id: UUID,
    token_service: Annotated[TokenTrackingService, Depends(get_token_tracking_service)],
) -> TokenUsageStats:
    """
    Get token usage statistics for a specific user.

    Args:
        user_id: User ID to get statistics for
        token_service: Token warning service instance

    Returns:
        TokenUsageStats: Aggregated token usage statistics
    """
    try:
        stats = await token_service.get_user_token_stats(user_id)
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving token statistics: {e!s}",
        ) from e


@router.get(
    "/session/{session_id}",
    summary="Get token warnings for a session",
    description="Retrieve token usage warnings for a specific conversation session",
    responses={
        200: {"description": "Session token warnings retrieved successfully"},
        404: {"description": "Session not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_session_warnings(
    session_id: str,
    token_service: Annotated[TokenTrackingService, Depends(get_token_tracking_service)],
    limit: int = Query(20, ge=1, le=100, description="Maximum number of warnings to return"),
    offset: int = Query(0, ge=0, description="Number of warnings to skip"),
) -> dict:
    """
    Get token warnings for a specific conversation session.

    Args:
        session_id: Session ID to get warnings for
        limit: Maximum number of warnings to return
        offset: Offset for pagination
        token_service: Token warning service instance

    Returns:
        Dictionary containing warnings and metadata
    """
    try:
        warnings = await token_service.get_session_warnings(session_id, limit, offset)
        return {
            "warnings": warnings,
            "session_id": session_id,
            "total": len(warnings),
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving session warnings: {e!s}",
        ) from e


@router.put(
    "/{warning_id}/acknowledge",
    summary="Acknowledge a token warning",
    description="Mark a token warning as acknowledged by the user",
    responses={
        200: {"description": "Token warning acknowledged successfully"},
        404: {"description": "Warning not found"},
        500: {"description": "Internal server error"},
    },
)
async def acknowledge_warning(
    warning_id: UUID,
    token_service: Annotated[TokenTrackingService, Depends(get_token_tracking_service)],
) -> dict:
    """
    Acknowledge a token warning.

    Args:
        warning_id: Warning ID to acknowledge
        token_service: Token warning service instance

    Returns:
        Success message with acknowledgment details
    """
    try:
        acknowledged_warning = await token_service.acknowledge_warning(warning_id)
        return {
            "message": "Warning acknowledged successfully",
            "warning_id": str(warning_id),
            "acknowledged_at": acknowledged_warning.acknowledged_at.isoformat()
            if acknowledged_warning.acknowledged_at
            else None,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error acknowledging warning: {e!s}",
        ) from e


@router.get(
    "/recent",
    summary="Get recent token warnings",
    description="Retrieve recent token warnings across all users (admin endpoint)",
    responses={
        200: {"description": "Recent token warnings retrieved successfully"},
        500: {"description": "Internal server error"},
    },
)
async def get_recent_warnings(
    token_service: Annotated[TokenTrackingService, Depends(get_token_tracking_service)],
    limit: int = Query(100, ge=1, le=500, description="Maximum number of warnings to return"),
    severity: str | None = Query(None, description="Filter by severity level"),
) -> dict:
    """
    Get recent token warnings across all users.

    Args:
        limit: Maximum number of warnings to return
        severity: Filter by severity level (info, warning, critical)
        token_service: Token warning service instance

    Returns:
        Dictionary containing recent warnings and metadata
    """
    try:
        warnings = await token_service.get_recent_warnings(limit, severity)
        return {
            "warnings": warnings,
            "total": len(warnings),
            "severity_filter": severity,
            "limit": limit,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving recent warnings: {e!s}",
        ) from e


@router.delete(
    "/{warning_id}",
    summary="Delete a token warning",
    description="Delete a specific token warning (admin endpoint)",
    responses={
        200: {"description": "Token warning deleted successfully"},
        404: {"description": "Warning not found"},
        500: {"description": "Internal server error"},
    },
)
async def delete_warning(
    warning_id: UUID,
    token_service: Annotated[TokenTrackingService, Depends(get_token_tracking_service)],
) -> dict:
    """
    Delete a specific token warning.

    Args:
        warning_id: Warning ID to delete
        token_service: Token warning service instance

    Returns:
        Success message
    """
    try:
        success = await token_service.delete_warning(warning_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warning not found")

        return {
            "message": "Warning deleted successfully",
            "warning_id": str(warning_id),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting warning: {e!s}",
        ) from e


@router.delete(
    "/user/{user_id}",
    summary="Delete all token warnings for a user",
    description="Delete all token warnings for a specific user (admin endpoint)",
    responses={
        200: {"description": "User token warnings deleted successfully"},
        500: {"description": "Internal server error"},
    },
)
async def delete_user_warnings(
    user_id: UUID,
    token_service: Annotated[TokenTrackingService, Depends(get_token_tracking_service)],
) -> dict:
    """
    Delete all token warnings for a specific user.

    Args:
        user_id: User ID to delete warnings for
        token_service: Token warning service instance

    Returns:
        Success message with count of deleted warnings
    """
    try:
        deleted_count = await token_service.delete_user_warnings(user_id)
        return {
            "message": f"Deleted {deleted_count} warnings for user",
            "user_id": str(user_id),
            "deleted_count": deleted_count,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting user warnings: {e!s}",
        ) from e
