"""REST API router for runtime configuration management.

This router provides endpoints for managing runtime configurations with
hierarchical precedence (collection > user > global > Settings fallback).
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import UUID4
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.config import Settings, get_settings
from core.custom_exceptions import NotFoundError, ValidationError
from core.logging_utils import get_logger
from rag_solution.core.dependencies import get_db, verify_user_access
from rag_solution.schemas.runtime_config_schema import (
    ConfigCategory,
    ConfigScope,
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


def verify_user_authorization(user: UserOutput, target_user_id: UUID4, operation: str) -> None:
    """Verify user is authorized to perform operation on target user's configs.

    Args:
        user: Authenticated user
        target_user_id: User ID being accessed
        operation: Operation being performed (for logging)

    Raises:
        HTTPException: 403 if user is not authorized
    """
    # Allow if user is accessing their own configs or is an admin
    if str(user.id) == str(target_user_id):
        return

    if user.role == "admin":
        logger.info("Admin user %s performing %s on user %s configs", user.id, operation, target_user_id)
        return

    logger.warning("User %s attempted unauthorized %s on user %s configs", user.id, operation, target_user_id)
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this user's configurations"
    )


def verify_global_config_authorization(user: UserOutput, config: RuntimeConfigOutput, operation: str) -> None:
    """Verify user is authorized to modify GLOBAL scope configurations (admin only).

    Args:
        user: Authenticated user
        config: Configuration being modified
        operation: Operation being performed (for logging)

    Raises:
        HTTPException: 403 if non-admin user attempts to modify GLOBAL config
    """
    if config.scope == ConfigScope.GLOBAL and user.role != "admin":
        logger.warning("Non-admin user %s attempted %s on GLOBAL config %s", user.id, operation, config.id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only administrators can modify global configurations"
        )


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
    - GLOBAL: No user_id or collection_id (admin only)
    - USER: Requires user_id, no collection_id
    - COLLECTION: Requires both user_id and collection_id

    Args:
        user_id: User ID from path (for authorization)
        config_input: Configuration input data
        user: Authenticated user
        service: Runtime configuration service

    Returns:
        RuntimeConfigOutput: Created configuration

    Raises:
        HTTPException: 400 for validation errors, 403 for authorization, 409 for unique constraint violations
    """
    # Authorization: Only admins can create GLOBAL configs, users can only create their own configs
    if config_input.scope == ConfigScope.GLOBAL:
        if user.role != "admin":
            logger.warning("Non-admin user %s attempted to create GLOBAL config", user.id)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Only administrators can create global configurations"
            )
    else:
        # For USER and COLLECTION scopes, verify user is accessing their own configs
        verify_user_authorization(user, user_id, "create")

        # Validate user_id in request body matches path parameter (prevents IDOR vulnerability)
        if config_input.user_id and str(config_input.user_id) != str(user_id):
            logger.warning(
                "User %s attempted to create config with mismatched user_id: path=%s, body=%s",
                user.id,
                user_id,
                config_input.user_id,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="user_id in request body must match path parameter"
            )

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
    except ValidationError as e:
        logger.warning("Validation error creating config: %s", e)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
    except ValueError as e:
        logger.error("Value error creating config: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except IntegrityError as e:
        logger.error("Integrity error creating config: %s", e)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Configuration with this scope/category/key combination already exists",
        ) from e
    except Exception as e:
        logger.exception("Unexpected error creating runtime config")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error") from e


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
        user_id: User ID from path (for authorization)
        config_id: Configuration UUID
        user: Authenticated user
        service: Runtime configuration service

    Returns:
        RuntimeConfigOutput: Configuration data

    Raises:
        HTTPException: 403 if not authorized, 404 if configuration not found
    """
    # Verify user is authorized to access this user's configs
    verify_user_authorization(user, user_id, "read")

    try:
        logger.debug("Getting runtime config: id=%s", config_id)
        config = service.get_config(config_id)
        return config
    except NotFoundError as e:
        logger.warning("Config not found: %s", e)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except ValueError as e:
        logger.warning("Value error getting config: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error getting runtime config %s", config_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error") from e


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
        user_id: User UUID
        category: Configuration category
        collection_id: Optional collection UUID for collection-scoped configs
        user: Authenticated user
        service: Runtime configuration service

    Returns:
        EffectiveConfig: Merged configuration with source tracking

    Raises:
        HTTPException: 400 for invalid category, 403 if not authorized
    """
    if not user or not service:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Service not available")

    # Verify user is authorized to access this user's configs
    verify_user_authorization(user, user_id, "read")

    try:
        logger.debug(
            "Getting effective config: user_id=%s, collection_id=%s, category=%s", user_id, collection_id, category
        )
        effective_config = service.get_effective_config(user_id, collection_id, category)
        logger.debug("Retrieved effective config with %d values", len(effective_config.values))
        return effective_config
    except ValueError as e:
        logger.warning("Invalid category: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error getting effective config")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error") from e


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
        user_id: User ID from path (for authorization)
        config_id: Configuration UUID
        updates: Dictionary of fields to update
        user: Authenticated user
        service: Runtime configuration service

    Returns:
        RuntimeConfigOutput: Updated configuration

    Raises:
        HTTPException: 403 if not authorized, 404 if not found, 400 for validation errors
    """
    # Verify user is authorized to modify this user's configs
    verify_user_authorization(user, user_id, "update")

    try:
        # First get the config to check if it's GLOBAL scope
        logger.info("Updating runtime config: id=%s with %d fields", config_id, len(updates))
        config = service.get_config(config_id)

        # Verify authorization to modify GLOBAL configs (admin only)
        verify_global_config_authorization(user, config, "update")

        # Proceed with update
        config = service.update_config(config_id, updates)
        logger.info("Updated runtime config: id=%s", config_id)
        return config
    except NotFoundError as e:
        logger.warning("Config not found: %s", e)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except ValidationError as e:
        logger.warning("Validation error updating config: %s", e)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
    except ValueError as e:
        logger.warning("Value error updating config: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error updating runtime config %s", config_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error") from e


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
        user_id: User ID from path (for authorization)
        config_id: Configuration UUID
        user: Authenticated user
        service: Runtime configuration service

    Raises:
        HTTPException: 403 if not authorized, 404 if configuration not found
    """
    # Verify user is authorized to delete this user's configs
    verify_user_authorization(user, user_id, "delete")

    try:
        # First get the config to check if it's GLOBAL scope
        logger.info("Deleting runtime config: id=%s", config_id)
        config = service.get_config(config_id)

        # Verify authorization to modify GLOBAL configs (admin only)
        verify_global_config_authorization(user, config, "delete")

        # Proceed with delete
        service.delete_config(config_id)
        logger.info("Deleted runtime config: id=%s", config_id)
    except NotFoundError as e:
        logger.warning("Config not found: %s", e)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except ValueError as e:
        logger.warning("Value error deleting config: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error deleting runtime config %s", config_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error") from e


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
        user_id: User ID from path (for authorization)
        config_id: Configuration UUID
        is_active: New active status
        user: Authenticated user
        service: Runtime configuration service

    Returns:
        RuntimeConfigOutput: Updated configuration

    Raises:
        HTTPException: 403 if not authorized, 404 if configuration not found
    """
    # Verify user is authorized to modify this user's configs
    verify_user_authorization(user, user_id, "toggle")

    try:
        # First get the config to check if it's GLOBAL scope
        logger.info("Toggling runtime config: id=%s to is_active=%s", config_id, is_active)
        config = service.get_config(config_id)

        # Verify authorization to modify GLOBAL configs (admin only)
        verify_global_config_authorization(user, config, "toggle")

        # Proceed with toggle
        config = service.toggle_config(config_id, is_active)
        logger.info("Toggled runtime config: id=%s", config_id)
        return config
    except NotFoundError as e:
        logger.warning("Config not found: %s", e)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except ValueError as e:
        logger.warning("Value error toggling config: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error toggling runtime config %s", config_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error") from e


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

    Raises:
        HTTPException: 403 if not authorized
    """
    if not user or not service:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Service not available")

    # Verify user is authorized to access this user's configs
    verify_user_authorization(user, user_id, "list")

    try:
        logger.debug("Listing user configs: user_id=%s, category=%s", user_id, category)
        configs = service.list_user_configs(user_id, category)
        logger.debug("Found %d user configs", len(configs))
        return configs
    except Exception as e:
        logger.exception("Unexpected error listing user configs")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error") from e


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
        user_id: User ID from path (for authorization)
        collection_id: Collection UUID
        category: Optional category filter
        user: Authenticated user
        service: Runtime configuration service

    Returns:
        list[RuntimeConfigOutput]: List of collection configurations

    Raises:
        HTTPException: 403 if not authorized
    """
    if not user or not service:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Service not available")

    # Verify user is authorized to access this user's configs
    verify_user_authorization(user, user_id, "list")

    try:
        logger.debug("Listing collection configs: collection_id=%s, category=%s", collection_id, category)
        configs = service.list_collection_configs(collection_id, category)
        logger.debug("Found %d collection configs", len(configs))
        return configs
    except Exception as e:
        logger.exception("Unexpected error listing collection configs")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error") from e
