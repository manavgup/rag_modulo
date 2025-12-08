"""Router for Agent Configuration API endpoints.

This module provides REST API endpoints for managing agent configurations
and collection-agent associations for the 3-stage search pipeline.

Endpoints:
    Agent Configurations:
    - POST /api/agent-configs - Create a new agent config
    - GET /api/agent-configs - List agent configs
    - GET /api/agent-configs/{config_id} - Get agent config by ID
    - PUT /api/agent-configs/{config_id} - Update agent config
    - DELETE /api/agent-configs/{config_id} - Delete agent config
    - GET /api/agent-configs/stages/{stage} - List configs by stage

    Collection-Agent Associations:
    - POST /api/collections/{collection_id}/agents - Add agent to collection
    - GET /api/collections/{collection_id}/agents - List collection agents
    - GET /api/collections/{collection_id}/agents/summary - Get agent summary
    - PUT /api/collections/{collection_id}/agents/{assoc_id} - Update association
    - DELETE /api/collections/{collection_id}/agents/{assoc_id} - Remove association
    - POST /api/collections/{collection_id}/agents/priorities - Batch update priorities

Reference: GitHub Issue #697
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import UUID4
from sqlalchemy.orm import Session

from core.logging_utils import get_logger
from rag_solution.core.exceptions import AlreadyExistsError, NotFoundError, ValidationError
from rag_solution.file_management.database import get_db
from rag_solution.schemas.agent_config_schema import (
    AgentConfigInput,
    AgentConfigListResponse,
    AgentConfigOutput,
    AgentConfigUpdate,
    BatchPriorityUpdate,
    CollectionAgentInput,
    CollectionAgentListResponse,
    CollectionAgentOutput,
    CollectionAgentUpdate,
)
from rag_solution.services.agent_config_service import AgentConfigService

logger = get_logger(__name__)

# ============================================================================
# Agent Configuration Router
# ============================================================================

config_router = APIRouter(
    prefix="/api/agent-configs",
    tags=["agent-configs"],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        404: {"description": "Agent config not found"},
    },
)


def get_current_user_id(request: Request) -> UUID4:
    """Extract current user ID from request state.

    Args:
        request: FastAPI request object

    Returns:
        User UUID

    Raises:
        HTTPException: If user not authenticated
    """
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    user_id = user.get("uuid") or user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not found in token",
        )

    return UUID4(user_id)


@config_router.post(
    "",
    response_model=AgentConfigOutput,
    status_code=status.HTTP_201_CREATED,
    summary="Create agent config",
    description="Create a new agent configuration for the search pipeline.",
)
async def create_agent_config(
    request: Request,
    config_input: AgentConfigInput,
    db: Session = Depends(get_db),
) -> AgentConfigOutput:
    """Create a new agent configuration.

    Args:
        request: FastAPI request object
        config_input: Agent config creation data
        db: Database session

    Returns:
        Created agent config
    """
    try:
        owner_user_id = get_current_user_id(request)
        service = AgentConfigService(db)
        return service.create_config(config_input, owner_user_id)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error("Error creating agent config: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create agent config",
        ) from e


@config_router.get(
    "",
    response_model=AgentConfigListResponse,
    summary="List agent configs",
    description="List agent configurations with optional filtering.",
)
async def list_agent_configs(
    request: Request,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    stage: str | None = Query(None, description="Filter by pipeline stage"),
    agent_type: str | None = Query(None, description="Filter by agent type"),
    config_status: str | None = Query(None, alias="status", description="Filter by status"),
    mine_only: bool = Query(False, description="Only show configs owned by current user"),
    include_system: bool = Query(True, description="Include system configs"),
    db: Session = Depends(get_db),
) -> AgentConfigListResponse:
    """List agent configurations with filtering.

    Args:
        request: FastAPI request object
        skip: Pagination offset
        limit: Maximum records
        stage: Filter by stage
        agent_type: Filter by type
        config_status: Filter by status
        mine_only: Only show owned configs
        include_system: Include system configs
        db: Database session

    Returns:
        Paginated list of configs
    """
    try:
        owner_user_id = None
        if mine_only:
            owner_user_id = get_current_user_id(request)

        service = AgentConfigService(db)
        return service.list_configs(
            skip=skip,
            limit=limit,
            owner_user_id=owner_user_id,
            stage=stage,
            agent_type=agent_type,
            status=config_status,
            include_system=include_system,
        )
    except Exception as e:
        logger.error("Error listing agent configs: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list agent configs",
        ) from e


@config_router.get(
    "/stages/{stage}",
    response_model=list[AgentConfigOutput],
    summary="List configs by stage",
    description="List active agent configurations for a specific pipeline stage.",
)
async def list_configs_by_stage(
    stage: str,
    include_system: bool = Query(True, description="Include system configs"),
    db: Session = Depends(get_db),
) -> list[AgentConfigOutput]:
    """List configs for a specific stage.

    Args:
        stage: Pipeline stage (pre_search, post_search, response)
        include_system: Include system configs
        db: Database session

    Returns:
        List of configs for the stage
    """
    try:
        service = AgentConfigService(db)
        return service.list_by_stage(stage, include_system)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error("Error listing configs by stage: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list configs by stage",
        ) from e


@config_router.get(
    "/{config_id}",
    response_model=AgentConfigOutput,
    summary="Get agent config",
    description="Get a specific agent configuration by ID.",
)
async def get_agent_config(
    config_id: UUID4,
    db: Session = Depends(get_db),
) -> AgentConfigOutput:
    """Get agent config by ID.

    Args:
        config_id: UUID of the config
        db: Database session

    Returns:
        Agent config
    """
    try:
        service = AgentConfigService(db)
        return service.get_config(config_id)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error("Error getting agent config %s: %s", config_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get agent config",
        ) from e


@config_router.put(
    "/{config_id}",
    response_model=AgentConfigOutput,
    summary="Update agent config",
    description="Update an existing agent configuration.",
)
async def update_agent_config(
    config_id: UUID4,
    config_update: AgentConfigUpdate,
    db: Session = Depends(get_db),
) -> AgentConfigOutput:
    """Update agent config.

    Args:
        config_id: UUID of the config
        config_update: Update data
        db: Database session

    Returns:
        Updated agent config
    """
    try:
        service = AgentConfigService(db)
        return service.update_config(config_id, config_update)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error("Error updating agent config %s: %s", config_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update agent config",
        ) from e


@config_router.delete(
    "/{config_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete agent config",
    description="Delete an agent configuration.",
)
async def delete_agent_config(
    config_id: UUID4,
    db: Session = Depends(get_db),
) -> None:
    """Delete agent config.

    Args:
        config_id: UUID of the config
        db: Database session
    """
    try:
        service = AgentConfigService(db)
        deleted = service.delete_config(config_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent config {config_id} not found",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting agent config %s: %s", config_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete agent config",
        ) from e


# ============================================================================
# Collection-Agent Association Router
# ============================================================================

collection_agent_router = APIRouter(
    prefix="/api/collections/{collection_id}/agents",
    tags=["collection-agents"],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        404: {"description": "Collection or association not found"},
    },
)


@collection_agent_router.post(
    "",
    response_model=CollectionAgentOutput,
    status_code=status.HTTP_201_CREATED,
    summary="Add agent to collection",
    description="Associate an agent configuration with a collection.",
)
async def add_agent_to_collection(
    collection_id: UUID4,
    association_input: CollectionAgentInput,
    db: Session = Depends(get_db),
) -> CollectionAgentOutput:
    """Add agent to collection.

    Args:
        collection_id: UUID of the collection
        association_input: Association data
        db: Database session

    Returns:
        Created association
    """
    try:
        service = AgentConfigService(db)
        return service.add_agent_to_collection(collection_id, association_input)
    except AlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error("Error adding agent to collection %s: %s", collection_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add agent to collection",
        ) from e


@collection_agent_router.get(
    "",
    response_model=CollectionAgentListResponse,
    summary="List collection agents",
    description="List all agents associated with a collection.",
)
async def list_collection_agents(
    collection_id: UUID4,
    stage: str | None = Query(None, description="Filter by pipeline stage"),
    enabled_only: bool = Query(False, description="Only show enabled agents"),
    db: Session = Depends(get_db),
) -> CollectionAgentListResponse:
    """List agents for a collection.

    Args:
        collection_id: UUID of the collection
        stage: Filter by stage
        enabled_only: Only enabled agents
        db: Database session

    Returns:
        List of associations
    """
    try:
        service = AgentConfigService(db)
        return service.list_collection_agents(
            collection_id=collection_id,
            stage=stage,
            enabled_only=enabled_only,
        )
    except Exception as e:
        logger.error("Error listing agents for collection %s: %s", collection_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list collection agents",
        ) from e


@collection_agent_router.get(
    "/summary",
    summary="Get agent summary",
    description="Get a summary of agents for a collection by stage.",
)
async def get_collection_agent_summary(
    collection_id: UUID4,
    db: Session = Depends(get_db),
) -> dict:
    """Get agent summary for a collection.

    Args:
        collection_id: UUID of the collection
        db: Database session

    Returns:
        Summary with counts per stage
    """
    try:
        service = AgentConfigService(db)
        return service.get_collection_agent_summary(collection_id)
    except Exception as e:
        logger.error("Error getting agent summary for collection %s: %s", collection_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get agent summary",
        ) from e


@collection_agent_router.put(
    "/{association_id}",
    response_model=CollectionAgentOutput,
    summary="Update association",
    description="Update a collection-agent association.",
)
async def update_collection_agent(
    collection_id: UUID4,
    association_id: UUID4,
    update_data: CollectionAgentUpdate,
    db: Session = Depends(get_db),
) -> CollectionAgentOutput:
    """Update collection-agent association.

    Args:
        collection_id: UUID of the collection (for validation)
        association_id: UUID of the association
        update_data: Update data
        db: Database session

    Returns:
        Updated association
    """
    try:
        service = AgentConfigService(db)
        # Verify association belongs to collection
        assoc = service.get_association(association_id)
        if assoc.collection_id != collection_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Association {association_id} not found in collection {collection_id}",
            )
        return service.update_association(association_id, update_data)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating association %s: %s", association_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update association",
        ) from e


@collection_agent_router.delete(
    "/{association_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove agent from collection",
    description="Remove an agent from a collection.",
)
async def remove_agent_from_collection(
    collection_id: UUID4,
    association_id: UUID4,
    db: Session = Depends(get_db),
) -> None:
    """Remove agent from collection.

    Args:
        collection_id: UUID of the collection
        association_id: UUID of the association
        db: Database session
    """
    try:
        service = AgentConfigService(db)
        # Verify association belongs to collection
        assoc = service.get_association(association_id)
        if assoc.collection_id != collection_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Association {association_id} not found in collection {collection_id}",
            )
        deleted = service.remove_agent_from_collection(association_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Association {association_id} not found",
            )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error removing association %s: %s", association_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove agent from collection",
        ) from e


@collection_agent_router.post(
    "/priorities",
    response_model=list[CollectionAgentOutput],
    summary="Batch update priorities",
    description="Batch update priorities for multiple collection-agent associations.",
)
async def batch_update_priorities(
    collection_id: UUID4,
    priority_update: BatchPriorityUpdate,
    db: Session = Depends(get_db),
) -> list[CollectionAgentOutput]:
    """Batch update priorities.

    Args:
        collection_id: UUID of the collection
        priority_update: Priority updates
        db: Database session

    Returns:
        List of updated associations
    """
    try:
        service = AgentConfigService(db)
        return service.batch_update_priorities(collection_id, priority_update.priorities)
    except Exception as e:
        logger.error("Error batch updating priorities for collection %s: %s", collection_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to batch update priorities",
        ) from e
