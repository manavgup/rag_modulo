"""Unit tests for MCP Pydantic schemas.

Tests the request/response validation schemas for MCP Gateway API endpoints.
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from rag_solution.schemas.mcp_schema import (
    MCPEnrichmentArtifact,
    MCPEnrichmentInput,
    MCPEnrichmentOutput,
    MCPHealthOutput,
    MCPToolDefinition,
    MCPToolInput,
    MCPToolListOutput,
    MCPToolOutput,
)


class TestMCPToolInput:
    """Test suite for MCPToolInput schema."""

    def test_valid_input(self):
        """Test valid tool input creation."""
        input_data = MCPToolInput(
            tool_name="powerpoint",
            arguments={"content": "test"},
        )

        assert input_data.tool_name == "powerpoint"
        assert input_data.arguments == {"content": "test"}
        assert input_data.timeout is None

    def test_with_timeout(self):
        """Test tool input with custom timeout."""
        input_data = MCPToolInput(
            tool_name="powerpoint",
            arguments={},
            timeout=60.0,
        )

        assert input_data.timeout == 60.0

    def test_empty_tool_name_rejected(self):
        """Test that empty tool name is rejected."""
        with pytest.raises(ValidationError):
            MCPToolInput(tool_name="", arguments={})

    def test_timeout_range_validation(self):
        """Test timeout range validation."""
        # Valid minimum
        MCPToolInput(tool_name="test", arguments={}, timeout=1.0)

        # Valid maximum
        MCPToolInput(tool_name="test", arguments={}, timeout=300.0)

        # Below minimum
        with pytest.raises(ValidationError):
            MCPToolInput(tool_name="test", arguments={}, timeout=0.5)

        # Above maximum
        with pytest.raises(ValidationError):
            MCPToolInput(tool_name="test", arguments={}, timeout=301.0)

    def test_extra_fields_forbidden(self):
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError):
            MCPToolInput(
                tool_name="test",
                arguments={},
                extra_field="not_allowed",
            )


class TestMCPToolOutput:
    """Test suite for MCPToolOutput schema."""

    def test_successful_output(self):
        """Test successful tool output."""
        output = MCPToolOutput(
            tool_name="powerpoint",
            success=True,
            result={"output": "content"},
            duration_ms=150.5,
        )

        assert output.tool_name == "powerpoint"
        assert output.success is True
        assert output.result == {"output": "content"}
        assert output.error is None
        assert output.duration_ms == 150.5

    def test_failed_output(self):
        """Test failed tool output."""
        output = MCPToolOutput(
            tool_name="powerpoint",
            success=False,
            error="Connection failed",
            duration_ms=50.0,
        )

        assert output.success is False
        assert output.error == "Connection failed"
        assert output.result is None


class TestMCPToolDefinition:
    """Test suite for MCPToolDefinition schema."""

    def test_tool_definition(self):
        """Test tool definition creation."""
        definition = MCPToolDefinition(
            name="powerpoint",
            description="Creates PowerPoint presentations",
            input_schema={"type": "object", "properties": {"content": {"type": "string"}}},
        )

        assert definition.name == "powerpoint"
        assert definition.description == "Creates PowerPoint presentations"
        assert "type" in definition.input_schema


class TestMCPToolListOutput:
    """Test suite for MCPToolListOutput schema."""

    def test_empty_list(self):
        """Test empty tool list."""
        output = MCPToolListOutput(tools=[], gateway_healthy=True)

        assert output.tools == []
        assert output.gateway_healthy is True

    def test_with_tools(self):
        """Test tool list with tools."""
        output = MCPToolListOutput(
            tools=[
                MCPToolDefinition(name="tool1", description="First"),
                MCPToolDefinition(name="tool2", description="Second"),
            ],
            gateway_healthy=True,
        )

        assert len(output.tools) == 2


class TestMCPEnrichmentInput:
    """Test suite for MCPEnrichmentInput schema."""

    def test_valid_enrichment_input(self):
        """Test valid enrichment input."""
        input_data = MCPEnrichmentInput(
            answer="Test answer",
            documents=[{"title": "Doc1", "content": "Content"}],
            query="Test query",
            collection_id=uuid4(),
            tools=["powerpoint"],
        )

        assert input_data.answer == "Test answer"
        assert len(input_data.documents) == 1
        assert input_data.tools == ["powerpoint"]

    def test_empty_answer_rejected(self):
        """Test that empty answer is rejected."""
        with pytest.raises(ValidationError):
            MCPEnrichmentInput(
                answer="",
                documents=[{"title": "Doc1"}],
                query="Test",
                collection_id=uuid4(),
                tools=["powerpoint"],
            )

    def test_empty_documents_rejected(self):
        """Test that empty documents list is rejected."""
        with pytest.raises(ValidationError):
            MCPEnrichmentInput(
                answer="Answer",
                documents=[],
                query="Test",
                collection_id=uuid4(),
                tools=["powerpoint"],
            )

    def test_empty_tools_rejected(self):
        """Test that empty tools list is rejected."""
        with pytest.raises(ValidationError):
            MCPEnrichmentInput(
                answer="Answer",
                documents=[{"title": "Doc1"}],
                query="Test",
                collection_id=uuid4(),
                tools=[],
            )

    def test_query_max_length(self):
        """Test query maximum length validation."""
        # Valid length
        MCPEnrichmentInput(
            answer="Answer",
            documents=[{"title": "Doc1"}],
            query="A" * 2000,
            collection_id=uuid4(),
            tools=["powerpoint"],
        )

        # Too long
        with pytest.raises(ValidationError):
            MCPEnrichmentInput(
                answer="Answer",
                documents=[{"title": "Doc1"}],
                query="A" * 2001,
                collection_id=uuid4(),
                tools=["powerpoint"],
            )


class TestMCPEnrichmentArtifact:
    """Test suite for MCPEnrichmentArtifact schema."""

    def test_artifact_creation(self):
        """Test artifact creation."""
        artifact = MCPEnrichmentArtifact(
            tool_name="powerpoint",
            artifact_type="presentation",
            content="base64-content",
            content_type="application/pptx",
            metadata={"slides": 5},
        )

        assert artifact.tool_name == "powerpoint"
        assert artifact.artifact_type == "presentation"
        assert artifact.metadata["slides"] == 5


class TestMCPEnrichmentOutput:
    """Test suite for MCPEnrichmentOutput schema."""

    def test_successful_enrichment(self):
        """Test successful enrichment output."""
        output = MCPEnrichmentOutput(
            original_answer="Test answer",
            artifacts=[
                MCPEnrichmentArtifact(
                    tool_name="powerpoint",
                    artifact_type="presentation",
                    content="content",
                    content_type="application/pptx",
                )
            ],
            enrichment_metadata={"tools_used": 1},
        )

        assert output.original_answer == "Test answer"
        assert len(output.artifacts) == 1
        assert output.errors == []

    def test_enrichment_with_errors(self):
        """Test enrichment output with errors."""
        output = MCPEnrichmentOutput(
            original_answer="Test answer",
            artifacts=[],
            errors=["Tool 'powerpoint' failed: timeout"],
        )

        assert output.original_answer == "Test answer"
        assert len(output.errors) == 1


class TestMCPHealthOutput:
    """Test suite for MCPHealthOutput schema."""

    def test_healthy_gateway(self):
        """Test healthy gateway output."""
        output = MCPHealthOutput(
            gateway_url="http://localhost:8080",
            healthy=True,
            circuit_breaker_state="closed",
            available_tools=5,
        )

        assert output.healthy is True
        assert output.circuit_breaker_state == "closed"
        assert output.available_tools == 5
        assert output.error is None

    def test_unhealthy_gateway(self):
        """Test unhealthy gateway output."""
        output = MCPHealthOutput(
            gateway_url="http://localhost:8080",
            healthy=False,
            circuit_breaker_state="open",
            available_tools=0,
            error="Connection refused",
        )

        assert output.healthy is False
        assert output.error == "Connection refused"

    def test_available_tools_non_negative(self):
        """Test available_tools must be non-negative."""
        with pytest.raises(ValidationError):
            MCPHealthOutput(
                gateway_url="http://localhost:8080",
                healthy=True,
                available_tools=-1,
            )
