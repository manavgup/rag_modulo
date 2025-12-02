"""RAG Modulo MCP Server.

This module exposes RAG Modulo functionality as an MCP (Model Context Protocol) server,
enabling LLMs to interact with RAG capabilities through standardized tool and resource interfaces.

The server provides:
- Tools: rag_search, rag_ingest, rag_list_collections, rag_generate_podcast,
         rag_smart_questions, rag_get_document
- Resources: Collection metadata, document lists, search result caches
- Authentication: SPIFFE JWT-SVID, Bearer tokens, API keys

Transports supported:
- stdio: For Claude Desktop and other stdio-based clients
- SSE: For web-based clients
- HTTP: For API clients via streamable-http
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

# Lazy imports to avoid import errors when optional dependencies are not installed


def create_mcp_server() -> "FastMCP":
    """Create and configure the MCP server with all RAG tools and resources."""
    from mcp_server.server import create_mcp_server as _create_mcp_server

    return _create_mcp_server()


def run_server(transport: str = "stdio", port: int = 8080) -> None:
    """Run the MCP server with the specified transport."""
    from mcp_server.server import run_server as _run_server

    _run_server(transport=transport, port=port)


__all__ = ["create_mcp_server", "run_server"]
