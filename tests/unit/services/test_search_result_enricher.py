"""Unit tests for Search Result Enricher.

Tests the SearchResultEnricher service including:
- Enrichment configuration
- Parallel and sequential execution
- Error handling and graceful degradation
- Integration with MCP client
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest

from rag_solution.schemas.mcp_schema import (
    MCPEnrichmentConfig,
    MCPInvocationOutput,
    MCPInvocationStatus,
    MCPTool,
    MCPToolsResponse,
)
from rag_solution.schemas.search_schema import SearchOutput
from vectordbs.data_types import DocumentChunkWithScore, DocumentMetadata, QueryResult


class TestSearchResultEnricher:
    """Test SearchResultEnricher."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock()
        settings.mcp_enabled = True
        settings.mcp_enrichment_enabled = True
        settings.mcp_gateway_url = "http://localhost:3000"
        settings.mcp_timeout = 30.0
        settings.mcp_health_timeout = 5.0
        settings.mcp_max_retries = 3
        settings.mcp_max_concurrent = 5
        settings.mcp_circuit_breaker_threshold = 5
        settings.mcp_circuit_breaker_timeout = 60.0
        settings.mcp_jwt_token = None
        return settings

    @pytest.fixture
    def mock_search_output(self):
        """Create mock search output."""
        return SearchOutput(
            answer="This is a test answer",
            documents=[
                DocumentMetadata(
                    document_name="test.pdf",
                    title="Test Document",
                    creation_date=datetime.utcnow(),
                )
            ],
            query_results=[
                QueryResult(
                    score=0.95,
                    chunk=DocumentChunkWithScore(
                        chunk_id="chunk1",
                        text="This is relevant text from the document.",
                        document_id="doc1",
                    ),
                )
            ],
            rewritten_query="test query",
            metadata={},
        )

    @pytest.fixture
    def enricher(self, mock_settings):
        """Create enricher instance."""
        from rag_solution.services.search_result_enricher import SearchResultEnricher

        return SearchResultEnricher(mock_settings)

    def test_enricher_initialization(self, enricher, mock_settings):
        """Test enricher initializes correctly."""
        assert enricher.settings == mock_settings
        assert enricher.max_concurrent == mock_settings.mcp_max_concurrent
        assert enricher._mcp_client is None  # Lazy initialization

    @pytest.mark.asyncio
    async def test_enrich_disabled_returns_original(self, enricher, mock_search_output, mock_settings):
        """Test enrichment returns original when disabled."""
        mock_settings.mcp_enabled = False

        result = await enricher.enrich(mock_search_output)

        assert result.answer == mock_search_output.answer
        assert result.documents == mock_search_output.documents

    @pytest.mark.asyncio
    async def test_enrich_config_disabled_returns_original(self, enricher, mock_search_output):
        """Test enrichment returns original when config disabled."""
        config = MCPEnrichmentConfig(enabled=False)

        result = await enricher.enrich(mock_search_output, config)

        assert result.answer == mock_search_output.answer

    @pytest.mark.asyncio
    async def test_enrich_gateway_unavailable(self, enricher, mock_search_output):
        """Test enrichment handles unavailable gateway gracefully."""
        mock_client = MagicMock()
        mock_client.is_available = AsyncMock(return_value=False)
        enricher._mcp_client = mock_client

        result = await enricher.enrich(mock_search_output)

        assert result.metadata is not None
        assert "mcp_enrichment" in result.metadata
        assert result.metadata["mcp_enrichment"]["success"] is False
        assert "unavailable" in result.metadata["mcp_enrichment"]["error"].lower()

    @pytest.mark.asyncio
    async def test_enrich_success_with_tools(self, enricher, mock_search_output):
        """Test successful enrichment with MCP tools."""
        mock_tools_response = MCPToolsResponse(
            tools=[
                MCPTool(
                    name="summarizer",
                    description="Summarizes content",
                    enabled=True,
                )
            ],
            total_count=1,
            gateway_healthy=True,
        )

        mock_invocation_result = MCPInvocationOutput(
            tool_name="summarizer",
            status=MCPInvocationStatus.SUCCESS,
            result={"summary": "Test summary"},
            execution_time_ms=100.0,
        )

        mock_client = MagicMock()
        mock_client.is_available = AsyncMock(return_value=True)
        mock_client.list_tools = AsyncMock(return_value=mock_tools_response)
        mock_client.invoke_tool = AsyncMock(return_value=mock_invocation_result)
        enricher._mcp_client = mock_client

        result = await enricher.enrich(mock_search_output)

        assert result.metadata is not None
        assert "mcp_enrichment" in result.metadata
        assert result.metadata["mcp_enrichment"]["success"] is True
        assert len(result.metadata["mcp_enrichment"]["tools"]) == 1
        assert result.metadata["mcp_enrichment"]["tools"][0]["name"] == "summarizer"
        assert result.metadata["mcp_enrichment"]["tools"][0]["success"] is True

    @pytest.mark.asyncio
    async def test_enrich_with_specific_tools(self, enricher, mock_search_output):
        """Test enrichment with specific tools configured."""
        config = MCPEnrichmentConfig(
            enabled=True,
            tools=["custom_tool"],
            timeout=10.0,
        )

        mock_invocation_result = MCPInvocationOutput(
            tool_name="custom_tool",
            status=MCPInvocationStatus.SUCCESS,
            result={"data": "custom result"},
            execution_time_ms=50.0,
        )

        mock_client = MagicMock()
        mock_client.is_available = AsyncMock(return_value=True)
        mock_client.invoke_tool = AsyncMock(return_value=mock_invocation_result)
        enricher._mcp_client = mock_client

        result = await enricher.enrich(mock_search_output, config)

        # Should use custom_tool from config
        mock_client.invoke_tool.assert_called_once()
        call_args = mock_client.invoke_tool.call_args
        assert call_args[0][0] == "custom_tool"

    @pytest.mark.asyncio
    async def test_enrich_parallel_execution(self, enricher, mock_search_output):
        """Test parallel enrichment execution."""
        config = MCPEnrichmentConfig(
            enabled=True,
            tools=["tool1", "tool2", "tool3"],
            parallel=True,
        )

        call_count = 0

        async def mock_invoke(name, args, timeout=None):
            nonlocal call_count
            call_count += 1
            return MCPInvocationOutput(
                tool_name=name,
                status=MCPInvocationStatus.SUCCESS,
                result={"data": f"result_{name}"},
                execution_time_ms=50.0,
            )

        mock_client = MagicMock()
        mock_client.is_available = AsyncMock(return_value=True)
        mock_client.invoke_tool = AsyncMock(side_effect=mock_invoke)
        enricher._mcp_client = mock_client

        result = await enricher.enrich(mock_search_output, config)

        # All tools should be called
        assert call_count == 3
        assert len(result.metadata["mcp_enrichment"]["tools"]) == 3

    @pytest.mark.asyncio
    async def test_enrich_sequential_execution(self, enricher, mock_search_output):
        """Test sequential enrichment execution."""
        config = MCPEnrichmentConfig(
            enabled=True,
            tools=["tool1", "tool2"],
            parallel=False,
        )

        execution_order = []

        async def mock_invoke(name, args, timeout=None):
            execution_order.append(name)
            return MCPInvocationOutput(
                tool_name=name,
                status=MCPInvocationStatus.SUCCESS,
                result={"data": f"result_{name}"},
                execution_time_ms=50.0,
            )

        mock_client = MagicMock()
        mock_client.is_available = AsyncMock(return_value=True)
        mock_client.invoke_tool = AsyncMock(side_effect=mock_invoke)
        enricher._mcp_client = mock_client

        await enricher.enrich(mock_search_output, config)

        # Should be in order for sequential execution
        assert execution_order == ["tool1", "tool2"]

    @pytest.mark.asyncio
    async def test_enrich_handles_tool_failure(self, enricher, mock_search_output):
        """Test enrichment handles individual tool failure gracefully."""
        config = MCPEnrichmentConfig(
            enabled=True,
            tools=["working_tool", "failing_tool"],
            fail_silently=True,
        )

        async def mock_invoke(name, args, timeout=None):
            if name == "failing_tool":
                return MCPInvocationOutput(
                    tool_name=name,
                    status=MCPInvocationStatus.ERROR,
                    error="Tool failed",
                    execution_time_ms=50.0,
                )
            return MCPInvocationOutput(
                tool_name=name,
                status=MCPInvocationStatus.SUCCESS,
                result={"data": "success"},
                execution_time_ms=50.0,
            )

        mock_client = MagicMock()
        mock_client.is_available = AsyncMock(return_value=True)
        mock_client.invoke_tool = AsyncMock(side_effect=mock_invoke)
        enricher._mcp_client = mock_client

        result = await enricher.enrich(mock_search_output, config)

        # Should still have results, with one success and one failure
        tools = result.metadata["mcp_enrichment"]["tools"]
        assert len(tools) == 2

        working = next(t for t in tools if t["name"] == "working_tool")
        failing = next(t for t in tools if t["name"] == "failing_tool")

        assert working["success"] is True
        assert failing["success"] is False
        assert failing["error"] == "Tool failed"

    @pytest.mark.asyncio
    async def test_enrich_preserves_original_output(self, enricher, mock_search_output):
        """Test enrichment doesn't modify original search output fields."""
        original_answer = mock_search_output.answer
        original_docs = mock_search_output.documents
        original_results = mock_search_output.query_results

        config = MCPEnrichmentConfig(enabled=True, tools=["tool1"])

        mock_client = MagicMock()
        mock_client.is_available = AsyncMock(return_value=True)
        mock_client.invoke_tool = AsyncMock(
            return_value=MCPInvocationOutput(
                tool_name="tool1",
                status=MCPInvocationStatus.SUCCESS,
                result={"modified": True},
                execution_time_ms=50.0,
            )
        )
        enricher._mcp_client = mock_client

        result = await enricher.enrich(mock_search_output, config)

        # Original fields should be unchanged
        assert result.answer == original_answer
        assert result.documents == original_docs
        assert result.query_results == original_results

    @pytest.mark.asyncio
    async def test_enrich_query_results_single_tool(self, enricher):
        """Test enriching individual query results with a tool."""
        query_results = [
            QueryResult(
                score=0.9,
                chunk=DocumentChunkWithScore(chunk_id="c1", text="Text 1", document_id="d1"),
            ),
            QueryResult(
                score=0.8,
                chunk=DocumentChunkWithScore(chunk_id="c2", text="Text 2", document_id="d2"),
            ),
        ]

        async def mock_invoke(name, args, timeout=None):
            return MCPInvocationOutput(
                tool_name=name,
                status=MCPInvocationStatus.SUCCESS,
                result={"entities": ["entity1"]},
                execution_time_ms=30.0,
            )

        mock_client = MagicMock()
        mock_client.invoke_tool = AsyncMock(side_effect=mock_invoke)
        enricher._mcp_client = mock_client

        results = await enricher.enrich_query_results(
            query_results,
            "entity_extractor",
            {"extract_types": ["person", "org"]},
        )

        assert len(results) == 2
        assert results[0].original_score == 0.9
        assert results[1].original_score == 0.8
        assert len(results[0].enrichments) == 1
        assert results[0].enrichments[0].success is True

    @pytest.mark.asyncio
    async def test_enrich_empty_tools_list(self, enricher, mock_search_output):
        """Test enrichment with no tools returns original."""
        mock_tools_response = MCPToolsResponse(
            tools=[],
            total_count=0,
            gateway_healthy=True,
        )

        mock_client = MagicMock()
        mock_client.is_available = AsyncMock(return_value=True)
        mock_client.list_tools = AsyncMock(return_value=mock_tools_response)
        enricher._mcp_client = mock_client

        result = await enricher.enrich(mock_search_output)

        # Should return original without enrichment metadata
        assert result.answer == mock_search_output.answer

    @pytest.mark.asyncio
    async def test_enrich_merges_with_existing_metadata(self, enricher):
        """Test enrichment merges with existing metadata."""
        search_output = SearchOutput(
            answer="Answer",
            documents=[],
            query_results=[],
            metadata={"existing_key": "existing_value"},
        )

        config = MCPEnrichmentConfig(enabled=True, tools=["tool1"])

        mock_client = MagicMock()
        mock_client.is_available = AsyncMock(return_value=True)
        mock_client.invoke_tool = AsyncMock(
            return_value=MCPInvocationOutput(
                tool_name="tool1",
                status=MCPInvocationStatus.SUCCESS,
                result={},
                execution_time_ms=50.0,
            )
        )
        enricher._mcp_client = mock_client

        result = await enricher.enrich(search_output, config)

        # Both old and new metadata should exist
        assert result.metadata["existing_key"] == "existing_value"
        assert "mcp_enrichment" in result.metadata


class TestEnrichmentConfig:
    """Test MCPEnrichmentConfig."""

    def test_default_config(self):
        """Test default enrichment configuration."""
        config = MCPEnrichmentConfig()

        assert config.enabled is True
        assert config.tools == []
        assert config.timeout == 30.0
        assert config.parallel is True
        assert config.fail_silently is True

    def test_custom_config(self):
        """Test custom enrichment configuration."""
        config = MCPEnrichmentConfig(
            enabled=True,
            tools=["tool1", "tool2"],
            timeout=15.0,
            parallel=False,
            fail_silently=False,
        )

        assert config.tools == ["tool1", "tool2"]
        assert config.timeout == 15.0
        assert config.parallel is False
        assert config.fail_silently is False
