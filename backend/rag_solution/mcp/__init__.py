"""MCP Gateway Integration for RAG Modulo.

This module provides a thin wrapper for integrating with MCP Context Forge Gateway,
enabling tool invocation and search result enrichment with production-grade
resilience patterns including circuit breaker, health checks, and rate limiting.

Architecture Decision:
    This implementation follows the "Simple Gateway Integration" approach recommended
    by expert panel (Martin Fowler, Sam Newman, Michael Nygard, Gregor Hohpe):
    - ~200 lines vs 2,000+ for complex agent framework
    - Leverages MCP Context Forge's existing 400+ tests
    - Includes production features: rate limiting, auth, circuit breaker

Modules:
    - gateway_client: ResilientMCPGatewayClient with circuit breaker and health checks
    - enricher: SearchResultEnricher for parallel result enhancement
    - mcp_schema: Pydantic schemas for request/response validation
"""

from rag_solution.mcp.enricher import SearchResultEnricher
from rag_solution.mcp.gateway_client import CircuitBreaker, CircuitBreakerOpenError, MCPGatewayClient

__all__ = [
    "CircuitBreaker",
    "CircuitBreakerOpenError",
    "MCPGatewayClient",
    "SearchResultEnricher",
]
