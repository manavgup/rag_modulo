"""Pydantic schemas for Agents."""

from pydantic import BaseModel, Field


class Agent(BaseModel):
    """Schema for an agent."""

    id: str = Field(..., description="The unique identifier of the agent.")
    name: str = Field(..., description="The name of the agent.")
    description: str | None = Field(None, description="A description of the agent.")


class AgentExecution(BaseModel):
    """Schema for executing an agent."""

    collection_id: str = Field(..., description="The ID of the collection to run the agent on.")
    params: dict = Field({}, description="The parameters for the agent.")