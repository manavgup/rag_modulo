"""CLI entry point for RAG Modulo MCP Server.

This module provides a command-line interface for running the MCP server
with different transport options.

Configuration:
    Default values come from environment variables (see .env.example):
    - MCP_SERVER_TRANSPORT: Default transport type (stdio, sse, http)
    - MCP_SERVER_PORT: Default port for SSE/HTTP transports

Usage:
    # Run with default transport from config (or stdio if not set)
    python -m mcp_server

    # Run with SSE transport on default port from config (or 8080)
    python -m mcp_server --transport sse

    # Run with SSE transport on custom port
    python -m mcp_server --transport sse --port 9000

    # Run with HTTP transport
    python -m mcp_server --transport http --port 8080
"""

import argparse
import logging
import sys

from core.config import get_settings
from core.enhanced_logging import get_logger
from mcp_server.server import run_server

logger = get_logger(__name__)

# Get config defaults
_settings = get_settings()


def main() -> None:
    """Main entry point for the MCP server CLI."""
    parser = argparse.ArgumentParser(
        description="RAG Modulo MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run with stdio transport (default, for Claude Desktop)
    python -m mcp_server

    # Run with SSE transport on port 8080
    python -m mcp_server --transport sse --port 8080

    # Run with HTTP transport on port 8080
    python -m mcp_server --transport http --port 8080
        """,
    )

    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "http"],
        default=_settings.mcp_server_transport,
        help=f"Transport type (default: {_settings.mcp_server_transport}, from MCP_SERVER_TRANSPORT)",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=_settings.mcp_server_port,
        help=f"Port for SSE/HTTP transports (default: {_settings.mcp_server_port}, from MCP_SERVER_PORT)",
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)",
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,  # Log to stderr to not interfere with stdio transport
    )

    logger = logging.getLogger("mcp_server")
    logger.info(
        "Starting RAG Modulo MCP Server with transport=%s, port=%d",
        args.transport,
        args.port,
    )

    try:
        run_server(transport=args.transport, port=args.port)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.exception("Server error: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
