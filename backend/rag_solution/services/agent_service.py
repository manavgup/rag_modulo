"""Service for interacting with external MCP agents."""

from typing import Any

import httpx
from fastapi import HTTPException, status

from core.config import get_settings
from rag_solution.schemas.agent_schema import Agent


class AgentService:
    """Service for handling agent-related operations."""

    def __init__(self) -> None:
        """Initialize the AgentService."""
        self.settings = get_settings()
        if not self.settings.external_agent_mcp_url:
            raise ValueError("EXTERNAL_AGENT_MCP_URL is not configured.")
        self.base_url = self.settings.external_agent_mcp_url

    async def list_agents(self) -> list[Agent]:
        """
        List available agents (tools) from the external MCP server.

        This corresponds to the MCP `get_tools` endpoint.
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.base_url}/tools")
                response.raise_for_status()
                tools_data = response.json()
                # Assuming the response is a list of tool definitions
                return [
                    Agent(id=tool.get("id"), name=tool.get("name"), description=tool.get("description"))
                    for tool in tools_data
                ]
            except httpx.RequestError as e:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Could not connect to external agent server: {e}",
                ) from e
            except httpx.HTTPStatusError as e:
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Error from external agent server: {e.response.text}",
                ) from e

    async def invoke_agent(self, agent_id: str, collection_id: str, params: dict[str, Any]) -> Any:
        """
        Invoke an agent on the external MCP server.

        This corresponds to the MCP `invoke_tool` endpoint.
        """
        payload = {
            "tool_id": agent_id,
            "parameters": {
                "collection_id": collection_id,
                **params,
            },
        }
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(f"{self.base_url}/invoke_tool", json=payload, timeout=300)
                response.raise_for_status()
                return response.json()
            except httpx.RequestError as e:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Could not connect to external agent server: {e}",
                ) from e
            except httpx.HTTPStatusError as e:
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Error from external agent server: {e.response.text}",
                ) from e


def get_agent_service() -> AgentService:
    """
    Get an instance of the AgentService.

    This function is designed for FastAPI dependency injection.
    """
    return AgentService()