import pytest
import httpx
import respx
from fastapi import HTTPException

from rag_solution.services.agent_service import AgentService
from core.config import get_settings, Settings

# Mock settings for testing
@pytest.fixture
def mock_settings() -> Settings:
    """Fixture to provide mock settings."""
    return Settings(EXTERNAL_AGENT_MCP_URL="http://fake-mcp-server.com/api")

@pytest.fixture
def agent_service(monkeypatch, mock_settings: Settings) -> AgentService:
    """Fixture to create an AgentService instance with mocked settings."""
    monkeypatch.setattr("rag_solution.services.agent_service.get_settings", lambda: mock_settings)
    return AgentService()

@respx.mock
async def test_list_agents_success(agent_service: AgentService):
    """Test listing agents successfully."""
    mock_route = respx.get("http://fake-mcp-server.com/api/tools").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"id": "agent1", "name": "Web Search", "description": "Searches the web."},
                {"id": "agent2", "name": "PowerPoint Generator", "description": "Generates presentations."},
            ],
        )
    )

    agents = await agent_service.list_agents()

    assert mock_route.called
    assert len(agents) == 2
    assert agents[0].id == "agent1"
    assert agents[0].name == "Web Search"
    assert agents[1].description == "Generates presentations."

@respx.mock
async def test_list_agents_http_error(agent_service: AgentService):
    """Test handling of HTTP error when listing agents."""
    respx.get("http://fake-mcp-server.com/api/tools").mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )

    with pytest.raises(HTTPException) as exc_info:
        await agent_service.list_agents()

    assert exc_info.value.status_code == 500
    assert "Internal Server Error" in exc_info.value.detail

@respx.mock
async def test_invoke_agent_success(agent_service: AgentService):
    """Test invoking an agent successfully."""
    mock_route = respx.post("http://fake-mcp-server.com/api/invoke_tool").mock(
        return_value=httpx.Response(200, json={"result": "success", "data": "some_data"})
    )

    result = await agent_service.invoke_agent("agent1", "collection123", {"query": "What is RAG?"})

    assert mock_route.called
    assert result == {"result": "success", "data": "some_data"}
    sent_request = mock_route.calls.last.request
    sent_payload = sent_request.content
    assert sent_payload is not None
    import json
    payload = json.loads(sent_payload)
    assert payload["tool_id"] == "agent1"
    assert payload["parameters"]["collection_id"] == "collection123"
    assert payload["parameters"]["query"] == "What is RAG?"

@respx.mock
async def test_invoke_agent_http_error(agent_service: AgentService):
    """Test handling of HTTP error when invoking an agent."""
    respx.post("http://fake-mcp-server.com/api/invoke_tool").mock(
        return_value=httpx.Response(400, text="Invalid parameters")
    )

    with pytest.raises(HTTPException) as exc_info:
        await agent_service.invoke_agent("agent1", "collection123", {})

    assert exc_info.value.status_code == 400
    assert "Invalid parameters" in exc_info.value.detail

def test_service_initialization_no_url(monkeypatch):
    """Test that AgentService raises an error if the URL is not configured."""
    mock_settings = Settings(EXTERNAL_AGENT_MCP_URL=None)
    monkeypatch.setattr("rag_solution.services.agent_service.get_settings", lambda: mock_settings)

    with pytest.raises(ValueError, match="EXTERNAL_AGENT_MCP_URL is not configured."):
        AgentService()