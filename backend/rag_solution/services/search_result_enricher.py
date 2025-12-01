"""Search Result Enricher using MCP tools.

This module implements the Content Enricher pattern as recommended by
Gregor Hohpe, maintaining clean separation between core search and
optional tool enrichment.

Key features:
- Parallel execution for efficiency
- Retry logic with exponential backoff
- Error isolation (enrichment failures don't break search)
- Configurable tool selection
- Graceful degradation
"""

import asyncio
import time
from typing import Any

from core.config import Settings
from core.logging_utils import get_logger
from rag_solution.schemas.mcp_schema import (
    MCPEnrichedSearchResult,
    MCPEnrichmentConfig,
    MCPEnrichmentResult,
    MCPInvocationStatus,
)
from rag_solution.schemas.search_schema import SearchOutput
from rag_solution.services.mcp_gateway_client import ResilientMCPGatewayClient
from vectordbs.data_types import QueryResult

logger = get_logger(__name__)


class SearchResultEnricher:
    """Enriches search results using MCP tools.

    Implements the Content Enricher pattern from Enterprise Integration Patterns:
    - Core search results pass through unchanged if enrichment fails
    - Enrichment is optional and non-blocking
    - Parallel execution for multiple tools
    - Error isolation prevents cascading failures

    Usage:
        settings = get_settings()
        enricher = SearchResultEnricher(settings)

        # Enrich search results
        config = MCPEnrichmentConfig(
            enabled=True,
            tools=["summarizer", "entity_extractor"],
            parallel=True
        )
        enriched_output = await enricher.enrich(search_output, config)

    Attributes:
        settings: Application settings
        mcp_client: MCP gateway client
        max_concurrent: Maximum concurrent enrichment operations
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize the search result enricher.

        Args:
            settings: Application settings with MCP configuration
        """
        self.settings = settings
        self._mcp_client: ResilientMCPGatewayClient | None = None
        self.max_concurrent = settings.mcp_max_concurrent
        self.default_timeout = settings.mcp_timeout

        logger.info(
            "Search result enricher initialized",
            extra={
                "mcp_enabled": settings.mcp_enabled,
                "enrichment_enabled": settings.mcp_enrichment_enabled,
                "max_concurrent": self.max_concurrent,
            },
        )

    @property
    def mcp_client(self) -> ResilientMCPGatewayClient:
        """Lazy-initialize MCP client."""
        if self._mcp_client is None:
            self._mcp_client = ResilientMCPGatewayClient(self.settings)
        return self._mcp_client

    async def enrich(
        self,
        search_output: SearchOutput,
        config: MCPEnrichmentConfig | None = None,
    ) -> SearchOutput:
        """Enrich search output with MCP tool results.

        This is the main entry point for enrichment. It:
        1. Checks if enrichment is enabled
        2. Validates MCP gateway availability
        3. Runs enrichment tools (parallel or sequential)
        4. Merges results into search output metadata

        Core search results are NEVER modified or removed - only metadata
        is added. This ensures graceful degradation.

        Args:
            search_output: Original search output to enrich
            config: Optional enrichment configuration

        Returns:
            SearchOutput with enrichment data in metadata field
        """
        # Use default config if not provided
        if config is None:
            config = MCPEnrichmentConfig(
                enabled=self.settings.mcp_enrichment_enabled,
                timeout=self.default_timeout,
            )

        # Skip if enrichment disabled
        if not config.enabled or not self.settings.mcp_enabled:
            logger.debug("Enrichment disabled, returning original results")
            return search_output

        start_time = time.perf_counter()

        try:
            # Check gateway availability
            if not await self.mcp_client.is_available():
                logger.warning("MCP gateway unavailable, skipping enrichment")
                return self._add_enrichment_metadata(
                    search_output,
                    success=False,
                    error="MCP gateway unavailable",
                    execution_time_ms=0,
                )

            # Get available tools if not specified
            tools_to_use = config.tools
            if not tools_to_use:
                tools_response = await self.mcp_client.list_tools()
                tools_to_use = [t.name for t in tools_response.tools if t.enabled]

            if not tools_to_use:
                logger.debug("No MCP tools available for enrichment")
                return search_output

            # Run enrichment
            if config.parallel:
                enrichment_results = await self._enrich_parallel(search_output, tools_to_use, config.timeout)
            else:
                enrichment_results = await self._enrich_sequential(search_output, tools_to_use, config.timeout)

            elapsed_ms = (time.perf_counter() - start_time) * 1000

            # Filter successful enrichments
            successful = [r for r in enrichment_results if r.success]
            failed = [r for r in enrichment_results if not r.success]

            logger.info(
                "Search result enrichment completed",
                extra={
                    "tools_used": len(tools_to_use),
                    "successful": len(successful),
                    "failed": len(failed),
                    "execution_time_ms": elapsed_ms,
                },
            )

            return self._merge_enrichments(
                search_output,
                enrichment_results,
                execution_time_ms=elapsed_ms,
            )

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "Enrichment failed with unexpected error",
                extra={
                    "error": str(e),
                    "execution_time_ms": elapsed_ms,
                },
                exc_info=True,
            )

            if config.fail_silently:
                return self._add_enrichment_metadata(
                    search_output,
                    success=False,
                    error=str(e),
                    execution_time_ms=elapsed_ms,
                )
            raise

    async def enrich_query_results(
        self,
        query_results: list[QueryResult],
        tool_name: str,
        tool_arguments: dict[str, Any] | None = None,
    ) -> list[MCPEnrichedSearchResult]:
        """Enrich individual query results with a specific tool.

        Useful for per-result enrichment like summarization or
        entity extraction on each chunk.

        Args:
            query_results: List of query results to enrich
            tool_name: Name of the MCP tool to use
            tool_arguments: Additional arguments for the tool

        Returns:
            List of enriched search results with tool output
        """
        if not self.settings.mcp_enabled:
            return [
                MCPEnrichedSearchResult(
                    original_score=qr.score,
                    enrichments=[],
                )
                for qr in query_results
            ]

        enriched_results = []
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def enrich_single(qr: QueryResult) -> MCPEnrichedSearchResult:
            async with semaphore:
                start_time = time.perf_counter()
                # Get text from chunk if available
                chunk_text = qr.chunk.text if qr.chunk and qr.chunk.text else ""
                args = {
                    "text": chunk_text,
                    **(tool_arguments or {}),
                }

                result = await self.mcp_client.invoke_tool(tool_name, args)
                elapsed_ms = (time.perf_counter() - start_time) * 1000

                enrichment = MCPEnrichmentResult(
                    tool_name=tool_name,
                    success=result.status == MCPInvocationStatus.SUCCESS,
                    data={"result": result.result} if result.result else None,
                    error=result.error,
                    execution_time_ms=elapsed_ms,
                )

                return MCPEnrichedSearchResult(
                    original_score=qr.score,
                    enrichments=[enrichment],
                )

        tasks = [enrich_single(qr) for qr in query_results]
        enriched_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions by returning non-enriched results
        final_results = []
        for i, result in enumerate(enriched_results):
            if isinstance(result, Exception):
                logger.warning(
                    "Failed to enrich query result",
                    extra={
                        "index": i,
                        "error": str(result),
                    },
                )
                final_results.append(
                    MCPEnrichedSearchResult(
                        original_score=query_results[i].score,
                        enrichments=[
                            MCPEnrichmentResult(
                                tool_name=tool_name,
                                success=False,
                                error=str(result),
                            )
                        ],
                    )
                )
            else:
                final_results.append(result)

        return final_results

    async def _enrich_parallel(
        self,
        search_output: SearchOutput,
        tools: list[str],
        timeout: float,
    ) -> list[MCPEnrichmentResult]:
        """Run enrichment tools in parallel.

        Uses semaphore to limit concurrency and prevent overwhelming
        the MCP gateway.

        Args:
            search_output: Search output to enrich
            tools: List of tool names to run
            timeout: Timeout per tool

        Returns:
            List of enrichment results
        """
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def run_tool(tool_name: str) -> MCPEnrichmentResult:
            async with semaphore:
                return await self._invoke_enrichment_tool(search_output, tool_name, timeout)

        tasks = [run_tool(tool) for tool in tools]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to error results
        enrichment_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(
                    "Parallel enrichment tool failed",
                    extra={
                        "tool": tools[i],
                        "error": str(result),
                    },
                )
                enrichment_results.append(
                    MCPEnrichmentResult(
                        tool_name=tools[i],
                        success=False,
                        error=str(result),
                    )
                )
            else:
                enrichment_results.append(result)

        return enrichment_results

    async def _enrich_sequential(
        self,
        search_output: SearchOutput,
        tools: list[str],
        timeout: float,
    ) -> list[MCPEnrichmentResult]:
        """Run enrichment tools sequentially.

        Useful when tools have dependencies or when order matters.

        Args:
            search_output: Search output to enrich
            tools: List of tool names to run
            timeout: Timeout per tool

        Returns:
            List of enrichment results
        """
        results = []
        for tool_name in tools:
            result = await self._invoke_enrichment_tool(search_output, tool_name, timeout)
            results.append(result)
        return results

    async def _invoke_enrichment_tool(
        self,
        search_output: SearchOutput,
        tool_name: str,
        timeout: float,
    ) -> MCPEnrichmentResult:
        """Invoke a single enrichment tool.

        Prepares arguments from search output and calls the MCP tool.

        Args:
            search_output: Search output providing context
            tool_name: Name of the tool to invoke
            timeout: Request timeout

        Returns:
            MCPEnrichmentResult with tool output
        """
        start_time = time.perf_counter()

        # Prepare tool arguments from search context
        arguments = {
            "query": search_output.rewritten_query or "",
            "answer": search_output.answer,
            "documents": [
                {
                    "document_name": doc.document_name,
                    "title": doc.title,
                    "content_type": getattr(doc, "content_type", None),
                }
                for doc in search_output.documents[:5]  # Limit to top 5
            ],
            "chunks": [
                {
                    "text": (qr.chunk.text[:500] if qr.chunk and qr.chunk.text else ""),  # Limit text length
                    "score": qr.score,
                }
                for qr in search_output.query_results[:5]
            ],
        }

        result = await self.mcp_client.invoke_tool(tool_name, arguments, timeout)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        return MCPEnrichmentResult(
            tool_name=tool_name,
            success=result.status == MCPInvocationStatus.SUCCESS,
            data={"result": result.result} if result.result else None,
            error=result.error,
            execution_time_ms=elapsed_ms,
        )

    def _merge_enrichments(
        self,
        search_output: SearchOutput,
        enrichments: list[MCPEnrichmentResult],
        execution_time_ms: float,
    ) -> SearchOutput:
        """Merge enrichment results into search output metadata.

        Does NOT modify original search results - only adds enrichment
        data to the metadata field.

        Args:
            search_output: Original search output
            enrichments: List of enrichment results
            execution_time_ms: Total enrichment time

        Returns:
            SearchOutput with enrichment metadata
        """
        # Prepare enrichment summary
        enrichment_data = {
            "mcp_enrichment": {
                "enabled": True,
                "success": any(e.success for e in enrichments),
                "execution_time_ms": execution_time_ms,
                "tools": [
                    {
                        "name": e.tool_name,
                        "success": e.success,
                        "data": e.data,
                        "error": e.error,
                        "execution_time_ms": e.execution_time_ms,
                    }
                    for e in enrichments
                ],
            }
        }

        # Merge with existing metadata
        existing_metadata = search_output.metadata or {}
        merged_metadata = {**existing_metadata, **enrichment_data}

        # Create new output with enrichment metadata
        return SearchOutput(
            answer=search_output.answer,
            documents=search_output.documents,
            query_results=search_output.query_results,
            rewritten_query=search_output.rewritten_query,
            evaluation=search_output.evaluation,
            execution_time=search_output.execution_time,
            cot_output=search_output.cot_output,
            metadata=merged_metadata,
            token_warning=search_output.token_warning,
            structured_answer=search_output.structured_answer,
        )

    def _add_enrichment_metadata(
        self,
        search_output: SearchOutput,
        success: bool,
        error: str | None = None,
        execution_time_ms: float = 0,
    ) -> SearchOutput:
        """Add basic enrichment metadata without actual enrichment.

        Used for error cases and when enrichment is skipped.

        Args:
            search_output: Original search output
            success: Whether enrichment was successful
            error: Error message if failed
            execution_time_ms: Time spent attempting enrichment

        Returns:
            SearchOutput with basic enrichment metadata
        """
        enrichment_data = {
            "mcp_enrichment": {
                "enabled": True,
                "success": success,
                "execution_time_ms": execution_time_ms,
                "error": error,
                "tools": [],
            }
        }

        existing_metadata = search_output.metadata or {}
        merged_metadata = {**existing_metadata, **enrichment_data}

        return SearchOutput(
            answer=search_output.answer,
            documents=search_output.documents,
            query_results=search_output.query_results,
            rewritten_query=search_output.rewritten_query,
            evaluation=search_output.evaluation,
            execution_time=search_output.execution_time,
            cot_output=search_output.cot_output,
            metadata=merged_metadata,
            token_warning=search_output.token_warning,
            structured_answer=search_output.structured_answer,
        )
