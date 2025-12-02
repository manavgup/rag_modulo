"""CLI entry point for RAG Modulo MCP Server.

This module provides a command-line interface for running the MCP server
with different transport options.

Usage:
    # Run with stdio transport (for Claude Desktop)
    python -m mcp_server

    # Run with SSE transport (for web clients)
    python -m mcp_server --transport sse --port 8080

    # Run with HTTP transport (for API clients)
    python -m mcp_server --transport http --port 8080
"""

import argparse
import logging
import sys

from backend.mcp_server.server import run_server


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
        default="stdio",
        help="Transport type (default: stdio)",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port for SSE/HTTP transports (default: 8080)",
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
