"""Router for Agent API endpoints.

This module provides REST API endpoints for managing AI agents with
SPIFFE-based workload identity.

Endpoints:
    POST /api/agents/register - Register a new agent
    POST /api/agents - Create a new agent
    GET /api/agents - List agents
    GET /api/agents/{agent_id} - Get agent by ID
    GET /api/agents/spiffe/{spiffe_id:path} - Get agent by SPIFFE ID
    PUT /api/agents/{agent_id} - Update agent
    DELETE /api/agents/{agent_id} - Delete agent
    POST /api/agents/{agent_id}/status - Update agent status
    POST /api/agents/{agent_id}/capabilities - Update agent capabilities
    POST /api/agents/validate - Validate SPIFFE JWT-SVID

Reference: docs/architecture/spire-integration-architecture.md
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import UUID4
from sqlalchemy.orm import Session

from core.logging_utils import get_logger
from rag_solution.core.exceptions import AlreadyExistsError, NotFoundError, ValidationError
from rag_solution.file_management.database import get_db
from rag_solution.schemas.agent_schema import (
    AgentCapabilityUpdate,
    AgentInput,
    AgentListResponse,
    AgentOutput,
    AgentRegistrationRequest,
    AgentRegistrationResponse,
    AgentStatusUpdate,
    AgentUpdate,
    SPIFFEValidationRequest,
    SPIFFEValidationResponse,
)
from rag_solution.services.agent_service import AgentService

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/agents",
    tags=["agents"],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        404: {"description": "Agent not found"},
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

    # Check if this is a user (not an agent)
    identity_type = user.get("identity_type", "user")
    if identity_type == "agent":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agent authentication not allowed for this endpoint",
        )

    user_id = user.get("uuid") or user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not found in token",
        )

    return UUID4(user_id)


@router.post(
    "/register",
    response_model=AgentRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new agent",
    description="Register a new AI agent and get SPIFFE ID with registration instructions.",
)
async def register_agent(
    request: Request,
    registration_request: AgentRegistrationRequest,
    db: Session = Depends(get_db),
) -> AgentRegistrationResponse:
    """Register a new agent with SPIFFE ID generation.

    This endpoint creates an agent record and returns the SPIFFE ID
    along with instructions for completing SPIRE registration.

    Args:
        request: FastAPI request object
        registration_request: Agent registration data
        db: Database session

    Returns:
        Registration response with agent data and SPIFFE ID
    """
    try:
        owner_user_id = get_current_user_id(request)
        service = AgentService(db)
        return service.register_agent(registration_request, owner_user_id)
    except AlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error("Error registering agent: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register agent",
        ) from e


@router.post(
    "",
    response_model=AgentOutput,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new agent",
    description="Create a new AI agent with the specified configuration.",
)
async def create_agent(
    request: Request,
    agent_input: AgentInput,
    db: Session = Depends(get_db),
) -> AgentOutput:
    """Create a new agent.

    Args:
        request: FastAPI request object
        agent_input: Agent creation data
        db: Database session

    Returns:
        Created agent data
    """
    try:
        owner_user_id = get_current_user_id(request)
        service = AgentService(db)
        return service.create_agent(agent_input, owner_user_id)
    except AlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error("Error creating agent: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create agent",
        ) from e


@router.get(
    "",
    response_model=AgentListResponse,
    summary="List agents",
    description="List agents with optional filtering and pagination.",
)
async def list_agents(
    request: Request,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    agent_type: str | None = Query(None, description="Filter by agent type"),
    agent_status: str | None = Query(None, alias="status", description="Filter by status"),
    team_id: UUID4 | None = Query(None, description="Filter by team ID"),
    mine_only: bool = Query(False, description="Only show agents owned by current user"),
    db: Session = Depends(get_db),
) -> AgentListResponse:
    """List agents with filtering and pagination.

    Args:
        request: FastAPI request object
        skip: Pagination offset
        limit: Maximum records
        agent_type: Filter by type
        agent_status: Filter by status
        team_id: Filter by team
        mine_only: Only show owned agents
        db: Database session

    Returns:
        Paginated agent list
    """
    try:
        owner_user_id = None
        if mine_only:
            owner_user_id = get_current_user_id(request)

        service = AgentService(db)
        return service.list_agents(
            skip=skip,
            limit=limit,
            owner_user_id=owner_user_id,
            team_id=team_id,
            agent_type=agent_type,
            status=agent_status,
        )
    except Exception as e:
        logger.error("Error listing agents: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list agents",
        ) from e


@router.get(
    "/{agent_id}",
    response_model=AgentOutput,
    summary="Get agent by ID",
    description="Get a specific agent by its UUID.",
)
async def get_agent(
    agent_id: UUID4,
    db: Session = Depends(get_db),
) -> AgentOutput:
    """Get an agent by ID.

    Args:
        agent_id: UUID of the agent
        db: Database session

    Returns:
        Agent data
    """
    try:
        service = AgentService(db)
        return service.get_agent(agent_id)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error("Error getting agent %s: %s", agent_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get agent",
        ) from e


@router.get(
    "/spiffe/{spiffe_id:path}",
    response_model=AgentOutput,
    summary="Get agent by SPIFFE ID",
    description="Get a specific agent by its SPIFFE ID.",
)
async def get_agent_by_spiffe_id(
    spiffe_id: str,
    db: Session = Depends(get_db),
) -> AgentOutput:
    """Get an agent by SPIFFE ID.

    Args:
        spiffe_id: Full SPIFFE ID (e.g., spiffe://domain/agent/type/id)
        db: Database session

    Returns:
        Agent data
    """
    try:
        service = AgentService(db)
        return service.get_agent_by_spiffe_id(spiffe_id)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error("Error getting agent by SPIFFE ID %s: %s", spiffe_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get agent",
        ) from e


@router.put(
    "/{agent_id}",
    response_model=AgentOutput,
    summary="Update agent",
    description="Update an existing agent's configuration.",
)
async def update_agent(
    agent_id: UUID4,
    agent_update: AgentUpdate,
    db: Session = Depends(get_db),
) -> AgentOutput:
    """Update an agent.

    Args:
        agent_id: UUID of the agent
        agent_update: Update data
        db: Database session

    Returns:
        Updated agent data
    """
    try:
        service = AgentService(db)
        return service.update_agent(agent_id, agent_update)
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
        logger.error("Error updating agent %s: %s", agent_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update agent",
        ) from e


@router.delete(
    "/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete agent",
    description="Delete an agent and revoke its SPIFFE ID.",
)
async def delete_agent(
    agent_id: UUID4,
    db: Session = Depends(get_db),
) -> None:
    """Delete an agent.

    Args:
        agent_id: UUID of the agent
        db: Database session
    """
    try:
        service = AgentService(db)
        deleted = service.delete_agent(agent_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting agent %s: %s", agent_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete agent",
        ) from e


@router.post(
    "/{agent_id}/status",
    response_model=AgentOutput,
    summary="Update agent status",
    description="Update an agent's status (active, suspended, revoked).",
)
async def update_agent_status(
    agent_id: UUID4,
    status_update: AgentStatusUpdate,
    db: Session = Depends(get_db),
) -> AgentOutput:
    """Update agent status.

    Args:
        agent_id: UUID of the agent
        status_update: Status update request
        db: Database session

    Returns:
        Updated agent data
    """
    try:
        service = AgentService(db)
        return service.update_agent_status(agent_id, status_update)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error("Error updating agent status %s: %s", agent_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update agent status",
        ) from e


@router.post(
    "/{agent_id}/capabilities",
    response_model=AgentOutput,
    summary="Update agent capabilities",
    description="Add or remove capabilities from an agent.",
)
async def update_agent_capabilities(
    agent_id: UUID4,
    capability_update: AgentCapabilityUpdate,
    db: Session = Depends(get_db),
) -> AgentOutput:
    """Update agent capabilities.

    Args:
        agent_id: UUID of the agent
        capability_update: Capabilities to add/remove
        db: Database session

    Returns:
        Updated agent data
    """
    try:
        service = AgentService(db)
        return service.update_agent_capabilities(agent_id, capability_update)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error("Error updating agent capabilities %s: %s", agent_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update agent capabilities",
        ) from e


@router.post(
    "/validate",
    response_model=SPIFFEValidationResponse,
    summary="Validate SPIFFE JWT-SVID",
    description="Validate a SPIFFE JWT-SVID token and return agent identity. Requires authentication.",
)
async def validate_spiffe_token(
    request: Request,
    validation_request: SPIFFEValidationRequest,
    db: Session = Depends(get_db),
) -> SPIFFEValidationResponse:
    """Validate a SPIFFE JWT-SVID.

    This endpoint allows validating JWT-SVIDs and extracting agent identity.
    Requires authentication to prevent SPIFFE ID enumeration attacks.

    Args:
        request: FastAPI request object
        validation_request: Token to validate
        db: Database session

    Returns:
        Validation response with agent identity

    Raises:
        HTTPException: If user not authenticated
    """
    # Require authentication to prevent enumeration attacks
    _ = get_current_user_id(request)

    try:
        service = AgentService(db)
        return service.validate_jwt_svid(validation_request)
    except Exception as e:
        logger.error("Error validating SPIFFE token: %s", e)
        return SPIFFEValidationResponse(
            valid=False,
            error=str(e),
        )


@router.post(
    "/{agent_id}/suspend",
    response_model=AgentOutput,
    summary="Suspend agent",
    description="Suspend an agent, preventing it from authenticating.",
)
async def suspend_agent(
    agent_id: UUID4,
    reason: str | None = Query(None, description="Reason for suspension"),
    db: Session = Depends(get_db),
) -> AgentOutput:
    """Suspend an agent.

    Args:
        agent_id: UUID of the agent
        reason: Optional suspension reason
        db: Database session

    Returns:
        Updated agent data
    """
    try:
        service = AgentService(db)
        return service.suspend_agent(agent_id, reason)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error("Error suspending agent %s: %s", agent_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to suspend agent",
        ) from e


@router.post(
    "/{agent_id}/activate",
    response_model=AgentOutput,
    summary="Activate agent",
    description="Activate a suspended agent.",
)
async def activate_agent(
    agent_id: UUID4,
    reason: str | None = Query(None, description="Reason for activation"),
    db: Session = Depends(get_db),
) -> AgentOutput:
    """Activate an agent.

    Args:
        agent_id: UUID of the agent
        reason: Optional activation reason
        db: Database session

    Returns:
        Updated agent data
    """
    try:
        service = AgentService(db)
        return service.activate_agent(agent_id, reason)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error("Error activating agent %s: %s", agent_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate agent",
        ) from e


@router.post(
    "/{agent_id}/revoke",
    response_model=AgentOutput,
    summary="Revoke agent",
    description="Revoke an agent's credentials permanently.",
)
async def revoke_agent(
    agent_id: UUID4,
    reason: str | None = Query(None, description="Reason for revocation"),
    db: Session = Depends(get_db),
) -> AgentOutput:
    """Revoke an agent.

    Args:
        agent_id: UUID of the agent
        reason: Optional revocation reason
        db: Database session

    Returns:
        Updated agent data
    """
    try:
        service = AgentService(db)
        return service.revoke_agent(agent_id, reason)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error("Error revoking agent %s: %s", agent_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke agent",
        ) from e
