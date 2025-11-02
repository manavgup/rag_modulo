"""REST API router for runtime configuration management.

This router provides endpoints for managing runtime configurations with
hierarchical precedence (collection > user > global > Settings fallback).
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import UUID4
from sqlalchemy.orm import Session

from core.config import Settings, get_settings
from core.logging_utils import get_logger
from rag_solution.core.dependencies import get_db, verify_user_access
from rag_solution.schemas.runtime_config_schema import (
    ConfigCategory,
    EffectiveConfig,
    RuntimeConfigInput,
    RuntimeConfigOutput,
)
from rag_solution.schemas.user_schema import UserOutput
from rag_solution.services.runtime_config_service import RuntimeConfigService

logger = get_logger("router.runtime_config")

router = APIRouter(prefix="/api/v1/runtime-configs", tags=["Runtime Configuration"])


def get_runtime_config_service(
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> RuntimeConfigService:
    """Get RuntimeConfigService instance with dependency injection."""
    return RuntimeConfigService(db, settings)


@router.post(
    "/{user_id}",
    response_model=RuntimeConfigOutput,
    status_code=status.HTTP_201_CREATED,
    summary="Create runtime configuration",
    description="Create a new runtime configuration with scope validation",
    responses={
        201: {"description": "Configuration created successfully"},
        400: {"description": "Invalid input or scope constraint violation"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized"},
        409: {"description": "Configuration already exists (unique constraint violation)"},
    },
)
async def create_runtime_config(
    user_id: UUID4,
    config_input: RuntimeConfigInput,
    user: Annotated[UserOutput, Depends(verify_user_access)],
    service: Annotated[RuntimeConfigService, Depends(get_runtime_config_service)],
) -> RuntimeConfigOutput:
    """Create a new runtime configuration.

    Validates scope constraints:
    - GLOBAL: No user_id or collection_id
    - USER: Requires user_id, no collection_id
    - COLLECTION: Requires both user_id and collection_id

    Args:
        config_input: Configuration input data
        user: Authenticated user
        service: Runtime configuration service

    Returns:
        RuntimeConfigOutput: Created configuration

    Raises:
        HTTPException: 400 for validation errors, 409 for unique constraint violations
    """
    try:
        logger.info(
            "Creating runtime config: scope=%s, category=%s, key=%s",
            config_input.scope,
            config_input.category,
            config_input.config_key,
        )
        config = service.create_config(config_input)
        logger.info("Created runtime config: id=%s", config.id)
        return config
    except ValueError as e:
        logger.error("Validation error creating config: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        logger.error("Error creating runtime config: %s", e)
        # Check for unique constraint violation
        if "unique constraint" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Configuration with this scope/category/key combination already exists",
            ) from e
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to create configuration: {e!s}"
        ) from e


@router.get(
    "/{user_id}/config/{config_id}",
    response_model=RuntimeConfigOutput,
    summary="Get runtime configuration",
    description="Retrieve a specific runtime configuration by ID",
    responses={
        200: {"description": "Configuration retrieved successfully"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized"},
        404: {"description": "Configuration not found"},
    },
)
async def get_runtime_config(
    user_id: UUID4,
    config_id: UUID4,
    user: Annotated[UserOutput, Depends(verify_user_access)],
    service: Annotated[RuntimeConfigService, Depends(get_runtime_config_service)],
) -> RuntimeConfigOutput:
    """Get a specific runtime configuration by ID.

    Args:
        config_id: Configuration UUID
        user: Authenticated user
        service: Runtime configuration service

    Returns:
        RuntimeConfigOutput: Configuration data

    Raises:
        HTTPException: 404 if configuration not found
    """
    try:
        logger.debug("Getting runtime config: id=%s", config_id)
        config = service.get_config(config_id)
        return config
    except Exception as e:
        logger.error("Error getting runtime config %s: %s", config_id, e)
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to retrieve configuration: {e!s}"
        ) from e


@router.get(
    "/{user_id}/effective/{category}",
    response_model=EffectiveConfig,
    summary="Get effective configuration",
    description="Get effective configuration with hierarchical precedence (collection > user > global > Settings)",
    responses={
        200: {"description": "Effective configuration retrieved successfully"},
        400: {"description": "Invalid category"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized"},
    },
)
async def get_effective_runtime_config(
    user_id: UUID4,
    category: ConfigCategory,
    collection_id: UUID4 | None = None,
    user: Annotated[UserOutput | None, Depends(verify_user_access)] = None,
    service: Annotated[RuntimeConfigService | None, Depends(get_runtime_config_service)] = None,
) -> EffectiveConfig:
    """Get effective configuration with hierarchical precedence.

    Implements precedence: collection > user > global > Settings

    Args:
        category: Configuration category
        user_id: User UUID
        collection_id: Optional collection UUID for collection-scoped configs
        user: Authenticated user
        service: Runtime configuration service

    Returns:
        EffectiveConfig: Merged configuration with source tracking

    Raises:
        HTTPException: 400 for invalid category
    """
    try:
        logger.debug("Getting effective config: user_id=%s, collection_id=%s, category=%s", user_id, collection_id, category)
        if not service:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Service not available")
        effective_config = service.get_effective_config(user_id, collection_id, category)
        logger.debug("Retrieved effective config with %d values", len(effective_config.values))
        return effective_config
    except ValueError as e:
        logger.error("Invalid category: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        logger.error("Error getting effective config: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to retrieve effective configuration: {e!s}"
        ) from e


@router.put(
    "/{user_id}/config/{config_id}",
    response_model=RuntimeConfigOutput,
    summary="Update runtime configuration",
    description="Update an existing runtime configuration",
    responses={
        200: {"description": "Configuration updated successfully"},
        400: {"description": "Invalid input or scope constraint violation"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized"},
        404: {"description": "Configuration not found"},
    },
)
async def update_runtime_config(
    user_id: UUID4,
    config_id: UUID4,
    updates: dict[str, Any],
    user: Annotated[UserOutput, Depends(verify_user_access)],
    service: Annotated[RuntimeConfigService, Depends(get_runtime_config_service)],
) -> RuntimeConfigOutput:
    """Update an existing runtime configuration.

    Validates scope constraints if scope, user_id, or collection_id are updated.

    Args:
        config_id: Configuration UUID
        updates: Dictionary of fields to update
        user: Authenticated user
        service: Runtime configuration service

    Returns:
        RuntimeConfigOutput: Updated configuration

    Raises:
        HTTPException: 404 if not found, 400 for validation errors
    """
    try:
        logger.info("Updating runtime config: id=%s with %d fields", config_id, len(updates))
        config = service.update_config(config_id, updates)
        logger.info("Updated runtime config: id=%s", config_id)
        return config
    except ValueError as e:
        logger.error("Validation error updating config: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        logger.error("Error updating runtime config %s: %s", config_id, e)
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to update configuration: {e!s}"
        ) from e


@router.delete(
    "/{user_id}/config/{config_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete runtime configuration",
    description="Delete an existing runtime configuration",
    responses={
        204: {"description": "Configuration deleted successfully"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized"},
        404: {"description": "Configuration not found"},
    },
)
async def delete_runtime_config(
    user_id: UUID4,
    config_id: UUID4,
    user: Annotated[UserOutput, Depends(verify_user_access)],
    service: Annotated[RuntimeConfigService, Depends(get_runtime_config_service)],
) -> None:
    """Delete a runtime configuration.

    Args:
        config_id: Configuration UUID
        user: Authenticated user
        service: Runtime configuration service

    Raises:
        HTTPException: 404 if configuration not found
    """
    try:
        logger.info("Deleting runtime config: id=%s", config_id)
        service.delete_config(config_id)
        logger.info("Deleted runtime config: id=%s", config_id)
    except Exception as e:
        logger.error("Error deleting runtime config %s: %s", config_id, e)
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete configuration: {e!s}"
        ) from e


@router.patch(
    "/{user_id}/config/{config_id}/toggle",
    response_model=RuntimeConfigOutput,
    summary="Toggle configuration active status",
    description="Enable or disable a runtime configuration",
    responses={
        200: {"description": "Configuration toggled successfully"},
        400: {"description": "Invalid input"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized"},
        404: {"description": "Configuration not found"},
    },
)
async def toggle_runtime_config(
    user_id: UUID4,
    config_id: UUID4,
    is_active: bool,
    user: Annotated[UserOutput, Depends(verify_user_access)],
    service: Annotated[RuntimeConfigService, Depends(get_runtime_config_service)],
) -> RuntimeConfigOutput:
    """Toggle active status of a runtime configuration.

    Args:
        config_id: Configuration UUID
        is_active: New active status
        user: Authenticated user
        service: Runtime configuration service

    Returns:
        RuntimeConfigOutput: Updated configuration

    Raises:
        HTTPException: 404 if configuration not found
    """
    try:
        logger.info("Toggling runtime config: id=%s to is_active=%s", config_id, is_active)
        config = service.toggle_config(config_id, is_active)
        logger.info("Toggled runtime config: id=%s", config_id)
        return config
    except Exception as e:
        logger.error("Error toggling runtime config %s: %s", config_id, e)
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to toggle configuration: {e!s}"
        ) from e


@router.get(
    "/user/{user_id}",
    response_model=list[RuntimeConfigOutput],
    summary="List user configurations",
    description="List all runtime configurations for a specific user",
    responses={
        200: {"description": "User configurations retrieved successfully"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized"},
    },
)
async def list_user_runtime_configs(
    user_id: UUID4,
    category: ConfigCategory | None = None,
    user: Annotated[UserOutput | None, Depends(verify_user_access)] = None,
    service: Annotated[RuntimeConfigService | None, Depends(get_runtime_config_service)] = None,
) -> list[RuntimeConfigOutput]:
    """List all runtime configurations for a user.

    Args:
        user_id: User UUID
        category: Optional category filter
        user: Authenticated user
        service: Runtime configuration service

    Returns:
        list[RuntimeConfigOutput]: List of user configurations
    """
    try:
        logger.debug("Listing user configs: user_id=%s, category=%s", user_id, category)
        if not service:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Service not available")
        configs = service.list_user_configs(user_id, category)
        logger.debug("Found %d user configs", len(configs))
        return configs
    except Exception as e:
        logger.error("Error listing user configs: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to list user configurations: {e!s}"
        ) from e


@router.get(
    "/{user_id}/collection/{collection_id}",
    response_model=list[RuntimeConfigOutput],
    summary="List collection configurations",
    description="List all runtime configurations for a specific collection",
    responses={
        200: {"description": "Collection configurations retrieved successfully"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized"},
    },
)
async def list_collection_runtime_configs(
    user_id: UUID4,
    collection_id: UUID4,
    category: ConfigCategory | None = None,
    user: Annotated[UserOutput | None, Depends(verify_user_access)] = None,
    service: Annotated[RuntimeConfigService | None, Depends(get_runtime_config_service)] = None,
) -> list[RuntimeConfigOutput]:
    """List all runtime configurations for a collection.

    Args:
        collection_id: Collection UUID
        category: Optional category filter
        user: Authenticated user
        service: Runtime configuration service

    Returns:
        list[RuntimeConfigOutput]: List of collection configurations
    """
    try:
        logger.debug("Listing collection configs: collection_id=%s, category=%s", collection_id, category)
        if not service:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Service not available")
        configs = service.list_collection_configs(collection_id, category)
        logger.debug("Found %d collection configs", len(configs))
        return configs
    except Exception as e:
        logger.error("Error listing collection configs: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list collection configurations: {e!s}",
        ) from e
