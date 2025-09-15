"""Specialized search CLI for RAG Modulo.

This module provides a focused CLI interface specifically for search operations,
enabling direct search queries without the overhead of the full CLI.
"""

import argparse
import sys
from collections.abc import Sequence

from .client import RAGAPIClient
from .commands.search import SearchCommands
from .config import RAGConfig
from .output import format_json_output, format_table_output, print_error, print_status


def create_search_parser() -> argparse.ArgumentParser:
    """Create the search CLI argument parser.

    Returns:
        Configured ArgumentParser instance for search operations
    """
    parser = argparse.ArgumentParser(
        prog="rag-search",
        description="RAG Modulo - Direct Search Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  rag-search "What is machine learning?" --collection abc123
  rag-search "Explain quantum computing" --collection abc123 --explain
  rag-search "Find similar docs" --collection abc123 --similar-to doc456
        """,
    )

    # Global options
    parser.add_argument("--profile", default="default", help="Configuration profile to use")
    parser.add_argument("--api-url", default="http://localhost:8000", help="RAG Modulo API base URL")
    parser.add_argument("--timeout", type=int, default=30, help="Request timeout in seconds")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--output", "-o", choices=["table", "json", "yaml"], default="table", help="Output format")

    # Search query (positional argument)
    parser.add_argument("query", help="Search query")

    # Collection (required)
    parser.add_argument("--collection", "-c", required=True, help="Collection ID to search")

    # Search options
    parser.add_argument("--pipeline", "-p", help="Pipeline ID to use")
    parser.add_argument("--max-chunks", type=int, default=5, help="Maximum chunks to retrieve")
    parser.add_argument("--similarity-threshold", type=float, default=0.7, help="Minimum similarity score")
    parser.add_argument("--max-results", type=int, default=10, help="Maximum number of results")

    # Search modes
    parser.add_argument("--explain", action="store_true", help="Show detailed search explanation")
    parser.add_argument("--semantic", action="store_true", help="Use semantic search only")
    parser.add_argument("--hybrid", action="store_true", help="Use hybrid search (semantic + keyword)")
    parser.add_argument("--similar-to", help="Find documents similar to this document ID")

    # Advanced options
    parser.add_argument("--show-retrieval", action="store_true", help="Show retrieval process details")
    parser.add_argument("--show-rewriting", action="store_true", help="Show query rewriting details")

    return parser


def main_search_cli(args: Sequence[str] | None = None) -> int:
    """Main search CLI entry point.

    Args:
        args: Command line arguments (None to use sys.argv)

    Returns:
        Exit code (0 for success)
    """
    parser = create_search_parser()

    try:
        # Parse arguments
        if args is None:
            args = sys.argv[1:]

        parsed_args = parser.parse_args(args)

        # Create configuration
        config = RAGConfig(
            api_url=parsed_args.api_url,
            profile=parsed_args.profile,
            timeout=parsed_args.timeout,
            output_format=parsed_args.output,
            verbose=parsed_args.verbose,
        )

        # Create API client and search commands
        api_client = RAGAPIClient(config)
        search_cmd = SearchCommands(api_client, config)

        # Execute search based on mode
        if parsed_args.explain:
            result = search_cmd.explain(
                collection_id=parsed_args.collection,
                query=parsed_args.query,
                show_retrieval=parsed_args.show_retrieval,
                show_rewriting=parsed_args.show_rewriting,
            )
        elif parsed_args.semantic:
            result = search_cmd.semantic_search(
                collection_id=parsed_args.collection,
                query=parsed_args.query,
                similarity_threshold=parsed_args.similarity_threshold,
                max_results=parsed_args.max_results,
            )
        elif parsed_args.hybrid:
            result = search_cmd.hybrid_search(
                collection_id=parsed_args.collection,
                query=parsed_args.query,
            )
        elif parsed_args.similar_to:
            result = search_cmd.search_similar_documents(
                document_id=parsed_args.similar_to,
                collection_id=parsed_args.collection,
                limit=parsed_args.max_results,
            )
        else:
            # Standard search
            result = search_cmd.query(
                collection_id=parsed_args.collection,
                query=parsed_args.query,
                pipeline_id=parsed_args.pipeline,
                max_chunks=parsed_args.max_chunks,
            )

        # Handle result
        if result.success:
            if config.output_format == "json":
                print(format_json_output(result.data or {}))
            elif config.output_format == "table" and result.data:
                if isinstance(result.data, list):
                    print(format_table_output(result.data))
                else:
                    print(format_json_output(result.data))
            else:
                print_status(result.message or "Search completed successfully", "success")
            return 0
        else:
            print_error(result.message or "Search failed")
            return 1

    except KeyboardInterrupt:
        print_status("Search cancelled by user", "warning")
        return 130
    except Exception as e:
        print_error(f"Search error: {e!s}")
        return 2


def main() -> None:
    """Main entry point for the rag-search command."""
    sys.exit(main_search_cli())


if __name__ == "__main__":
    main()
