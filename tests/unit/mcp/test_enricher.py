"""Unit tests for MCP Search Result Enricher.

Tests the SearchResultEnricher service including:
- Parallel tool invocation
- Error isolation
- Artifact extraction
- Graceful degradation
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from rag_solution.mcp.enricher import EnrichmentArtifact, EnrichmentResult, SearchResultEnricher
from rag_solution.mcp.gateway_client import MCPGatewayClient, MCPToolResult


class TestEnrichmentArtifact:
    """Test suite for EnrichmentArtifact dataclass."""

    def test_artifact_creation(self):
        """Test creating an enrichment artifact."""
        artifact = EnrichmentArtifact(
            tool_name="powerpoint",
            artifact_type="presentation",
            content="base64-encoded-content",
            content_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            metadata={"slides": 5},
        )

        assert artifact.tool_name == "powerpoint"
        assert artifact.artifact_type == "presentation"
        assert artifact.content == "base64-encoded-content"
        assert artifact.metadata["slides"] == 5


class TestEnrichmentResult:
    """Test suite for EnrichmentResult dataclass."""

    def test_empty_result(self):
        """Test creating an empty enrichment result."""
        result = EnrichmentResult(original_answer="Test answer")

        assert result.original_answer == "Test answer"
        assert result.artifacts == []
        assert result.errors == []

    def test_result_with_artifacts(self):
        """Test enrichment result with artifacts."""
        artifact = EnrichmentArtifact(
            tool_name="powerpoint",
            artifact_type="presentation",
            content="content",
            content_type="application/pptx",
        )
        result = EnrichmentResult(
            original_answer="Answer",
            artifacts=[artifact],
            enrichment_metadata={"tools_used": 1},
        )

        assert len(result.artifacts) == 1
        assert result.enrichment_metadata["tools_used"] == 1


class TestSearchResultEnricher:
    """Test suite for SearchResultEnricher class."""

    @pytest.fixture
    def mock_mcp_client(self):
        """Create a mocked MCP Gateway client."""
        client = MagicMock(spec=MCPGatewayClient)
        client.invoke_tool = AsyncMock()
        client.list_tools = AsyncMock()
        return client

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.mcp_gateway_url = "http://localhost:8080"
        settings.mcp_gateway_timeout = 30.0
        return settings

    @pytest.fixture
    def enricher(self, mock_mcp_client, mock_settings):
        """Create an enricher instance with mocked dependencies."""
        return SearchResultEnricher(
            mcp_client=mock_mcp_client,
            settings=mock_settings,
            max_concurrent_tools=3,
            enrichment_timeout=60.0,
        )

    @pytest.fixture
    def sample_documents(self):
        """Create sample documents for testing."""
        return [
            {"title": "Doc 1", "content": "Content of document 1"},
            {"title": "Doc 2", "content": "Content of document 2"},
        ]

    @pytest.mark.asyncio
    async def test_enrich_without_tool_hints(self, enricher, sample_documents):
        """Test enrichment without tool hints returns original result."""
        result = await enricher.enrich_results(
            answer="Test answer",
            documents=sample_documents,
            query="Test query",
            collection_id=uuid4(),
            tool_hints=None,
        )

        assert result.original_answer == "Test answer"
        assert result.artifacts == []
        assert result.errors == []

    @pytest.mark.asyncio
    async def test_enrich_with_empty_tool_hints(self, enricher, sample_documents):
        """Test enrichment with empty tool hints."""
        result = await enricher.enrich_results(
            answer="Test answer",
            documents=sample_documents,
            query="Test query",
            collection_id=uuid4(),
            tool_hints=[],
        )

        assert result.original_answer == "Test answer"
        assert result.artifacts == []

    @pytest.mark.asyncio
    async def test_enrich_with_unsupported_tools(self, enricher, sample_documents):
        """Test enrichment with unsupported tools."""
        result = await enricher.enrich_results(
            answer="Test answer",
            documents=sample_documents,
            query="Test query",
            collection_id=uuid4(),
            tool_hints=["unsupported_tool"],
        )

        assert result.original_answer == "Test answer"
        assert result.artifacts == []
        # Should not call invoke_tool for unsupported tools
        enricher.mcp_client.invoke_tool.assert_not_called()

    @pytest.mark.asyncio
    async def test_enrich_successful_tool_invocation(self, enricher, sample_documents):
        """Test successful tool invocation produces artifact."""
        enricher.mcp_client.invoke_tool.return_value = MCPToolResult(
            tool_name="powerpoint",
            success=True,
            result={"content": "presentation-content"},
            duration_ms=100.0,
        )

        result = await enricher.enrich_results(
            answer="Test answer",
            documents=sample_documents,
            query="Test query",
            collection_id=uuid4(),
            tool_hints=["powerpoint"],
        )

        assert result.original_answer == "Test answer"
        assert len(result.artifacts) == 1
        assert result.artifacts[0].tool_name == "powerpoint"
        assert result.errors == []

    @pytest.mark.asyncio
    async def test_enrich_failed_tool_invocation(self, enricher, sample_documents):
        """Test failed tool invocation records error."""
        enricher.mcp_client.invoke_tool.return_value = MCPToolResult(
            tool_name="powerpoint",
            success=False,
            error="Connection failed",
            duration_ms=50.0,
        )

        result = await enricher.enrich_results(
            answer="Test answer",
            documents=sample_documents,
            query="Test query",
            collection_id=uuid4(),
            tool_hints=["powerpoint"],
        )

        assert result.original_answer == "Test answer"
        assert result.artifacts == []
        assert len(result.errors) == 1
        assert "powerpoint" in result.errors[0]
        assert "Connection failed" in result.errors[0]

    @pytest.mark.asyncio
    async def test_enrich_multiple_tools(self, enricher, sample_documents):
        """Test enrichment with multiple tools."""
        # Set up different results for different tools
        async def mock_invoke(tool_name, arguments):
            if tool_name == "powerpoint":
                return MCPToolResult(
                    tool_name="powerpoint",
                    success=True,
                    result={"content": "ppt-content"},
                )
            return MCPToolResult(
                tool_name="visualization",
                success=True,
                result={"content": "viz-content"},
            )

        enricher.mcp_client.invoke_tool = AsyncMock(side_effect=mock_invoke)

        result = await enricher.enrich_results(
            answer="Test answer",
            documents=sample_documents,
            query="Test query",
            collection_id=uuid4(),
            tool_hints=["powerpoint", "visualization"],
        )

        assert len(result.artifacts) == 2
        assert enricher.mcp_client.invoke_tool.call_count == 2

    @pytest.mark.asyncio
    async def test_enrich_partial_failure(self, enricher, sample_documents):
        """Test enrichment with partial failure (some tools succeed, some fail)."""
        async def mock_invoke(tool_name, arguments):
            if tool_name == "powerpoint":
                return MCPToolResult(
                    tool_name="powerpoint",
                    success=True,
                    result={"content": "ppt-content"},
                )
            return MCPToolResult(
                tool_name="visualization",
                success=False,
                error="Timeout",
            )

        enricher.mcp_client.invoke_tool = AsyncMock(side_effect=mock_invoke)

        result = await enricher.enrich_results(
            answer="Test answer",
            documents=sample_documents,
            query="Test query",
            collection_id=uuid4(),
            tool_hints=["powerpoint", "visualization"],
        )

        assert len(result.artifacts) == 1
        assert result.artifacts[0].tool_name == "powerpoint"
        assert len(result.errors) == 1
        assert "visualization" in result.errors[0]

    @pytest.mark.asyncio
    async def test_enrich_timeout(self, enricher, sample_documents):
        """Test enrichment timeout handling."""
        import asyncio

        async def slow_invoke(tool_name, arguments):
            await asyncio.sleep(5)  # Longer than timeout
            return MCPToolResult(tool_name=tool_name, success=True, result={})

        enricher.mcp_client.invoke_tool = AsyncMock(side_effect=slow_invoke)
        enricher.enrichment_timeout = 0.1  # Short timeout for test

        result = await enricher.enrich_results(
            answer="Test answer",
            documents=sample_documents,
            query="Test query",
            collection_id=uuid4(),
            tool_hints=["powerpoint"],
        )

        assert result.original_answer == "Test answer"
        assert len(result.errors) == 1
        assert "timed out" in result.errors[0]
        assert result.enrichment_metadata.get("timeout") is True

    @pytest.mark.asyncio
    async def test_enrich_exception_handling(self, enricher, sample_documents):
        """Test enrichment handles unexpected exceptions gracefully."""
        enricher.mcp_client.invoke_tool = AsyncMock(side_effect=Exception("Unexpected error"))

        result = await enricher.enrich_results(
            answer="Test answer",
            documents=sample_documents,
            query="Test query",
            collection_id=uuid4(),
            tool_hints=["powerpoint"],
        )

        assert result.original_answer == "Test answer"
        assert len(result.errors) >= 1
        # Original answer should always be preserved

    @pytest.mark.asyncio
    async def test_get_available_tools(self, enricher):
        """Test getting available tools from gateway."""
        enricher.mcp_client.list_tools.return_value = [
            {"name": "powerpoint"},
            {"name": "visualization"},
            {"name": "unknown_tool"},
        ]

        available = await enricher.get_available_tools()

        assert "powerpoint" in available
        assert "visualization" in available
        assert "unknown_tool" not in available  # Not in SUPPORTED_TOOLS

    @pytest.mark.asyncio
    async def test_get_available_tools_gateway_error(self, enricher):
        """Test getting available tools when gateway errors."""
        enricher.mcp_client.list_tools.side_effect = Exception("Gateway error")

        available = await enricher.get_available_tools()

        assert available == []

    def test_build_tool_arguments_powerpoint(self, enricher, sample_documents):
        """Test building arguments for PowerPoint tool."""
        args = enricher._build_tool_arguments(
            "powerpoint",
            "Test answer",
            sample_documents,
            "Test query",
        )

        assert "title" in args
        assert "content" in args
        assert "sources" in args
        assert args["content"] == "Test answer"

    def test_build_tool_arguments_visualization(self, enricher, sample_documents):
        """Test building arguments for visualization tool."""
        args = enricher._build_tool_arguments(
            "visualization",
            "Test answer",
            sample_documents,
            "Test query",
        )

        assert "data" in args
        assert "chart_type" in args

    def test_extract_artifact_success(self, enricher):
        """Test artifact extraction from successful result."""
        result = MCPToolResult(
            tool_name="powerpoint",
            success=True,
            result={"content": "test-content"},
            duration_ms=100.0,
        )

        artifact = enricher._extract_artifact("powerpoint", result)

        assert artifact is not None
        assert artifact.tool_name == "powerpoint"
        assert artifact.content == "test-content"
        assert artifact.metadata["duration_ms"] == 100.0

    def test_extract_artifact_no_content(self, enricher):
        """Test artifact extraction with no content."""
        result = MCPToolResult(
            tool_name="powerpoint",
            success=True,
            result={},  # No content
        )

        artifact = enricher._extract_artifact("powerpoint", result)

        assert artifact is None

    def test_supported_tools_mapping(self, enricher):
        """Test supported tools mapping is correct."""
        assert "powerpoint" in enricher.SUPPORTED_TOOLS
        assert "visualization" in enricher.SUPPORTED_TOOLS
        assert "chart" in enricher.SUPPORTED_TOOLS
        assert "pdf_export" in enricher.SUPPORTED_TOOLS

    def test_enricher_initialization(self, mock_mcp_client, mock_settings):
        """Test enricher initialization with custom parameters."""
        enricher = SearchResultEnricher(
            mcp_client=mock_mcp_client,
            settings=mock_settings,
            max_concurrent_tools=5,
            enrichment_timeout=120.0,
        )

        assert enricher.max_concurrent_tools == 5
        assert enricher.enrichment_timeout == 120.0
