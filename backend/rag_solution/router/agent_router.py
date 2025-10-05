"""API router for agents."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from rag_solution.schemas.agent_schema import Agent, AgentExecution
from rag_solution.services.agent_service import AgentService, get_agent_service

router = APIRouter()


@router.get("/agents", response_model=list[Agent])
async def list_agents(
    agent_service: AgentService = Depends(get_agent_service),
) -> list[Agent]:
    """Get a list of available agents."""
    try:
        return await agent_service.list_agents()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post("/agents/{agent_id}/invoke")
async def invoke_agent(
    agent_id: str,
    execution: AgentExecution,
    agent_service: AgentService = Depends(get_agent_service),
) -> Any:
    """Invoke an agent."""
    try:
        result = await agent_service.invoke_agent(
            agent_id=agent_id,
            collection_id=execution.collection_id,
            params=execution.params,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e