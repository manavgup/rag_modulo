"""Main CLI entry point and argument parsing for RAG Modulo.

This module provides the main CLI interface using argparse, defining all
commands, subcommands, and their arguments. It follows the argparse-based
approach for better enterprise reliability and testing.
"""

import argparse
import sys
from collections.abc import Sequence

from .config import RAGConfig
from .exceptions import RAGCLIError


class CLIResult:
    """Result of CLI command execution.

    This class standardizes the return value from CLI commands,
    providing consistent exit codes and output handling.
    """

    def __init__(self, exit_code: int = 0, output: str = "", error: str | None = None) -> None:
        """Initialize CLI result.

        Args:
            exit_code: Command exit code (0 for success)
            output: Command output text
            error: Error message if command failed
        """
        self.exit_code = exit_code
        self.output = output
        self.error = error


def create_main_parser() -> argparse.ArgumentParser:
    """Create the main argument parser for RAG CLI.

    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        prog="rag-cli",
        description="RAG Modulo - Comprehensive CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  rag-cli auth login --username user@example.com
  rag-cli collections list --output json
  rag-cli documents upload collection123 document.pdf
  rag-cli search query collection123 "What is machine learning?"
  rag-cli health check --api --database
        """,
    )

    # Global options
    parser.add_argument("--profile", default="default", help="Configuration profile to use (default: default)")
    parser.add_argument(
        "--api-url",
        dest="api_url",
        default="http://localhost:8000",
        help="RAG Modulo API base URL (default: http://localhost:8000)",
    )
    parser.add_argument("--timeout", type=int, default=30, help="Request timeout in seconds (default: 30)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument(
        "--output", "-o", choices=["table", "json", "yaml"], default="table", help="Output format (default: table)"
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--version", action="version", version="rag-cli 0.1.0")

    # Create subparsers for commands
    subparsers = parser.add_subparsers(
        dest="command",
        title="Available Commands",
        description="Use 'rag-cli <command> --help' for command-specific help",
        help="Command to execute",
    )

    # Authentication commands
    _add_auth_commands(subparsers)

    # User management commands
    _add_user_commands(subparsers)

    # Collection management commands
    _add_collection_commands(subparsers)

    # Document management commands
    _add_document_commands(subparsers)

    # Search commands
    _add_search_commands(subparsers)

    # Health check commands
    _add_health_commands(subparsers)

    # Configuration commands
    _add_config_commands(subparsers)

    # Provider management commands
    _add_provider_commands(subparsers)

    # Pipeline management commands
    _add_pipeline_commands(subparsers)

    return parser


def _add_auth_commands(subparsers: argparse._SubParsersAction) -> None:
    """Add authentication subcommands.

    Args:
        subparsers: Subparsers action from main parser
    """
    auth_parser = subparsers.add_parser(
        "auth", help="Authentication management", description="Manage authentication and profiles"
    )

    auth_subparsers = auth_parser.add_subparsers(dest="auth_command", help="Authentication commands")

    # Login command
    login_parser = auth_subparsers.add_parser("login", help="Login to RAG Modulo")
    login_parser.add_argument("--username", help="Username/email (required for local auth)")
    login_parser.add_argument("--password", help="Password (will prompt if not provided)")
    login_parser.add_argument(
        "--provider", choices=["local", "ibm"], default="local", help="Authentication provider (default: local)"
    )
    login_parser.add_argument("--no-interactive", action="store_true", help="Disable interactive prompts")

    # Set token command
    token_parser = auth_subparsers.add_parser("set-token", help="Set authentication token directly")
    token_parser.add_argument("token", help="JWT authentication token")
    token_parser.add_argument(
        "--expires-in", type=int, default=86400, help="Token expiration in seconds (default: 86400/24 hours)"
    )

    # Logout command
    logout_parser = auth_subparsers.add_parser("logout", help="Logout from RAG Modulo")
    logout_parser.add_argument("--all-profiles", action="store_true", help="Logout from all profiles")

    # Profile management
    profiles_parser = auth_subparsers.add_parser("profiles", help="Manage authentication profiles")
    profiles_subparsers = profiles_parser.add_subparsers(dest="profiles_command", help="Profile commands")

    # List profiles
    profiles_subparsers.add_parser("list", help="List available profiles")

    # Create profile
    create_profile_parser = profiles_subparsers.add_parser("create", help="Create new profile")
    create_profile_parser.add_argument("name", help="Profile name")
    create_profile_parser.add_argument("--api-url", required=True, help="API URL for this profile")
    create_profile_parser.add_argument("--description", help="Profile description")

    # Switch profile
    switch_profile_parser = profiles_subparsers.add_parser("switch", help="Switch to profile")
    switch_profile_parser.add_argument("name", help="Profile name to switch to")

    # Delete profile
    delete_profile_parser = profiles_subparsers.add_parser("delete", help="Delete profile")
    delete_profile_parser.add_argument("name", help="Profile name to delete")
    delete_profile_parser.add_argument("--force", action="store_true", help="Force deletion without confirmation")


def _add_user_commands(subparsers: argparse._SubParsersAction) -> None:
    """Add user management subcommands.

    Args:
        subparsers: Subparsers action from main parser
    """
    users_parser = subparsers.add_parser("users", help="User management", description="Manage users and permissions")

    users_subparsers = users_parser.add_subparsers(dest="users_command", help="User commands")

    # List users
    list_users_parser = users_subparsers.add_parser("list", help="List users")
    list_users_parser.add_argument("--role", help="Filter by role")
    list_users_parser.add_argument("--team", help="Filter by team")
    list_users_parser.add_argument("--active", action="store_true", help="Show only active users")

    # Create user
    create_user_parser = users_subparsers.add_parser("create", help="Create new user")
    create_user_parser.add_argument("email", help="User email address")
    create_user_parser.add_argument("--name", required=True, help="User full name")
    create_user_parser.add_argument("--role", default="user", choices=["user", "admin"], help="User role")
    create_user_parser.add_argument("--teams", nargs="*", help="Team assignments")

    # Show user details
    show_user_parser = users_subparsers.add_parser("show", help="Show user details")
    show_user_parser.add_argument("user_id", help="User ID or email")

    # Update user
    update_user_parser = users_subparsers.add_parser("update", help="Update user")
    update_user_parser.add_argument("user_id", help="User ID or email")
    update_user_parser.add_argument("--name", help="Update user name")
    update_user_parser.add_argument("--role", choices=["user", "admin"], help="Update user role")
    update_user_parser.add_argument("--active", type=bool, help="Update active status")

    # Delete user
    delete_user_parser = users_subparsers.add_parser("delete", help="Delete user")
    delete_user_parser.add_argument("user_id", help="User ID or email")
    delete_user_parser.add_argument("--force", action="store_true", help="Force deletion without confirmation")


def _add_collection_commands(subparsers: argparse._SubParsersAction) -> None:
    """Add collection management subcommands.

    Args:
        subparsers: Subparsers action from main parser
    """
    collections_parser = subparsers.add_parser(
        "collections", help="Collection management", description="Manage document collections"
    )

    collections_subparsers = collections_parser.add_subparsers(dest="collections_command", help="Collection commands")

    # List collections
    list_collections_parser = collections_subparsers.add_parser("list", help="List collections")
    list_collections_parser.add_argument("--private", action="store_true", help="Show only private collections")
    list_collections_parser.add_argument("--shared", action="store_true", help="Show only shared collections")
    list_collections_parser.add_argument("--team", help="Filter by team")

    # Create collection
    create_collection_parser = collections_subparsers.add_parser("create", help="Create new collection")
    create_collection_parser.add_argument("name", help="Collection name")
    create_collection_parser.add_argument("--description", help="Collection description")
    create_collection_parser.add_argument("--vector-db", default="milvus", help="Vector database to use")
    create_collection_parser.add_argument("--private", action="store_true", help="Make collection private")

    # Show collection details
    show_collection_parser = collections_subparsers.add_parser("show", help="Show collection details")
    show_collection_parser.add_argument("collection_id", help="Collection ID")
    show_collection_parser.add_argument("--include-stats", action="store_true", help="Include statistics")

    # Update collection
    update_collection_parser = collections_subparsers.add_parser("update", help="Update collection")
    update_collection_parser.add_argument("collection_id", help="Collection ID")
    update_collection_parser.add_argument("--name", help="Update collection name")
    update_collection_parser.add_argument("--description", help="Update description")

    # Delete collection
    delete_collection_parser = collections_subparsers.add_parser("delete", help="Delete collection")
    delete_collection_parser.add_argument("collection_id", help="Collection ID")
    delete_collection_parser.add_argument("--force", action="store_true", help="Force deletion without confirmation")

    # Share collection
    share_collection_parser = collections_subparsers.add_parser("share", help="Share collection")
    share_collection_parser.add_argument("collection_id", help="Collection ID")
    share_collection_parser.add_argument("--users", nargs="*", help="User IDs to share with")
    share_collection_parser.add_argument(
        "--permission", default="read", choices=["read", "write"], help="Permission level"
    )


def _add_document_commands(subparsers: argparse._SubParsersAction) -> None:
    """Add document management subcommands.

    Args:
        subparsers: Subparsers action from main parser
    """
    documents_parser = subparsers.add_parser(
        "documents", help="Document management", description="Manage documents in collections"
    )

    documents_subparsers = documents_parser.add_subparsers(dest="documents_command", help="Document commands")

    # Upload document
    upload_parser = documents_subparsers.add_parser("upload", help="Upload document")
    upload_parser.add_argument("collection_id", help="Collection ID")
    upload_parser.add_argument("file_path", help="Path to document file")
    upload_parser.add_argument("--chunk-strategy", default="semantic", help="Chunking strategy")
    upload_parser.add_argument("--metadata", help="Additional metadata (JSON string)")

    # List documents
    list_documents_parser = documents_subparsers.add_parser("list", help="List documents")
    list_documents_parser.add_argument("collection_id", help="Collection ID")
    list_documents_parser.add_argument("--format", help="Filter by file format")
    list_documents_parser.add_argument("--status", help="Filter by processing status")

    # Show document details
    show_document_parser = documents_subparsers.add_parser("show", help="Show document details")
    show_document_parser.add_argument("document_id", help="Document ID")

    # Delete document
    delete_document_parser = documents_subparsers.add_parser("delete", help="Delete document")
    delete_document_parser.add_argument("document_id", help="Document ID")
    delete_document_parser.add_argument("--force", action="store_true", help="Force deletion without confirmation")

    # Batch upload
    batch_upload_parser = documents_subparsers.add_parser("batch-upload", help="Upload multiple documents")
    batch_upload_parser.add_argument("collection_id", help="Collection ID")
    batch_upload_parser.add_argument("--files-list", help="File containing list of file paths")
    batch_upload_parser.add_argument("--directory", help="Directory containing files to upload")
    batch_upload_parser.add_argument("--chunk-strategy", default="semantic", help="Chunking strategy")


def _add_search_commands(subparsers: argparse._SubParsersAction) -> None:
    """Add search subcommands.

    Args:
        subparsers: Subparsers action from main parser
    """
    search_parser = subparsers.add_parser(
        "search", help="Search operations", description="Search documents and collections"
    )

    search_subparsers = search_parser.add_subparsers(dest="search_command", help="Search commands")

    # Query search
    query_parser = search_subparsers.add_parser("query", help="Search documents")
    query_parser.add_argument("collection_id", help="Collection ID to search")
    query_parser.add_argument("query", help="Search query")
    query_parser.add_argument("--pipeline-id", help="Pipeline ID to use")
    query_parser.add_argument("--max-chunks", type=int, default=5, help="Maximum chunks to retrieve")

    # Explain search
    explain_parser = search_subparsers.add_parser("explain", help="Explain search results")
    explain_parser.add_argument("collection_id", help="Collection ID to search")
    explain_parser.add_argument("query", help="Search query")
    explain_parser.add_argument("--show-retrieval", action="store_true", help="Show retrieval details")
    explain_parser.add_argument("--show-rewriting", action="store_true", help="Show query rewriting")

    # Batch search
    batch_parser = search_subparsers.add_parser("batch", help="Batch search queries")
    batch_parser.add_argument("collection_id", help="Collection ID to search")
    batch_parser.add_argument("queries_file", help="File containing queries (JSON)")


def _add_health_commands(subparsers: argparse._SubParsersAction) -> None:
    """Add health check subcommands.

    Args:
        subparsers: Subparsers action from main parser
    """
    health_parser = subparsers.add_parser(
        "health", help="System health checks", description="Check system component health"
    )

    health_subparsers = health_parser.add_subparsers(dest="health_command", help="Health check commands")

    # Check health
    check_parser = health_subparsers.add_parser("check", help="Check system health")
    check_parser.add_argument("--api", action="store_true", help="Check API health")
    check_parser.add_argument("--database", action="store_true", help="Check database health")
    check_parser.add_argument("--vector-db", action="store_true", help="Check vector database health")
    check_parser.add_argument("--timeout", type=int, default=30, help="Health check timeout")


def _add_config_commands(subparsers: argparse._SubParsersAction) -> None:
    """Add configuration subcommands.

    Args:
        subparsers: Subparsers action from main parser
    """
    config_parser = subparsers.add_parser(
        "config", help="Configuration management", description="Manage CLI configuration"
    )

    config_subparsers = config_parser.add_subparsers(dest="config_command", help="Configuration commands")

    # Show config
    config_subparsers.add_parser("show", help="Show current configuration")

    # Validate config
    validate_parser = config_subparsers.add_parser("validate", help="Validate configuration")
    validate_parser.add_argument("--api-url", help="API URL to validate")
    validate_parser.add_argument("--timeout", type=int, help="Timeout to validate")

    # Reset config
    reset_parser = config_subparsers.add_parser("reset", help="Reset configuration")
    reset_parser.add_argument("--force", action="store_true", help="Force reset without confirmation")


def _add_provider_commands(subparsers: argparse._SubParsersAction) -> None:
    """Add provider management subcommands.

    Args:
        subparsers: Subparsers action from main parser
    """
    providers_parser = subparsers.add_parser(
        "providers", help="Provider management", description="Manage LLM providers"
    )

    providers_subparsers = providers_parser.add_subparsers(dest="providers_command", help="Provider commands")

    # List providers
    list_providers_parser = providers_subparsers.add_parser("list", help="List providers")
    list_providers_parser.add_argument("--available", action="store_true", help="Show only available provider types")
    list_providers_parser.add_argument("--configured", action="store_true", help="Show only configured providers")

    # Create provider
    create_provider_parser = providers_subparsers.add_parser("create", help="Create new provider")
    create_provider_parser.add_argument("name", help="Provider name")
    create_provider_parser.add_argument("type", help="Provider type (openai, anthropic, watsonx, etc.)")
    create_provider_parser.add_argument("--api-key", help="API key for the provider")
    create_provider_parser.add_argument("--endpoint", help="Custom endpoint URL")
    create_provider_parser.add_argument("--model", help="Default model to use")
    create_provider_parser.add_argument("--test", action="store_true", help="Test connection after creation")

    # Show provider details
    show_provider_parser = providers_subparsers.add_parser("show", help="Show provider details")
    show_provider_parser.add_argument("provider_id", help="Provider ID")

    # Update provider
    update_provider_parser = providers_subparsers.add_parser("update", help="Update provider")
    update_provider_parser.add_argument("provider_id", help="Provider ID")
    update_provider_parser.add_argument("--api-key", help="Update API key")
    update_provider_parser.add_argument("--endpoint", help="Update endpoint URL")
    update_provider_parser.add_argument("--model", help="Update default model")

    # Delete provider
    delete_provider_parser = providers_subparsers.add_parser("delete", help="Delete provider")
    delete_provider_parser.add_argument("provider_id", help="Provider ID")
    delete_provider_parser.add_argument("--force", action="store_true", help="Force deletion without confirmation")
    delete_provider_parser.add_argument("--migrate-pipelines-to", help="Provider ID to migrate pipelines to")

    # Test provider
    test_provider_parser = providers_subparsers.add_parser("test", help="Test provider")
    test_provider_parser.add_argument("provider_id", help="Provider ID")
    test_provider_parser.add_argument("--query", help="Test query to send")
    test_provider_parser.add_argument("--verbose", action="store_true", help="Include detailed test results")


def _add_pipeline_commands(subparsers: argparse._SubParsersAction) -> None:
    """Add pipeline management subcommands.

    Args:
        subparsers: Subparsers action from main parser
    """
    pipelines_parser = subparsers.add_parser(
        "pipelines", help="Pipeline management", description="Manage search pipelines"
    )

    pipelines_subparsers = pipelines_parser.add_subparsers(dest="pipelines_command", help="Pipeline commands")

    # List pipelines
    list_pipelines_parser = pipelines_subparsers.add_parser("list", help="List pipelines")
    list_pipelines_parser.add_argument("--collection", help="Filter by collection ID")
    list_pipelines_parser.add_argument("--user", help="Filter by user ID")
    list_pipelines_parser.add_argument("--provider", help="Filter by provider ID")

    # Create pipeline
    create_pipeline_parser = pipelines_subparsers.add_parser("create", help="Create new pipeline")
    create_pipeline_parser.add_argument("name", help="Pipeline name")
    create_pipeline_parser.add_argument("--llm-provider", help="LLM provider ID")
    create_pipeline_parser.add_argument("--parameters", help="Pipeline parameters (JSON string)")
    create_pipeline_parser.add_argument("--template", help="Template ID to use")

    # Show pipeline details
    show_pipeline_parser = pipelines_subparsers.add_parser("show", help="Show pipeline details")
    show_pipeline_parser.add_argument("pipeline_id", help="Pipeline ID")
    show_pipeline_parser.add_argument("--include-config", action="store_true", help="Include configuration details")
    show_pipeline_parser.add_argument("--include-performance", action="store_true", help="Include performance metrics")

    # Update pipeline
    update_pipeline_parser = pipelines_subparsers.add_parser("update", help="Update pipeline")
    update_pipeline_parser.add_argument("pipeline_id", help="Pipeline ID")
    update_pipeline_parser.add_argument("--provider", help="Update LLM provider ID")
    update_pipeline_parser.add_argument("--parameters", help="Update pipeline parameters (JSON string)")

    # Delete pipeline
    delete_pipeline_parser = pipelines_subparsers.add_parser("delete", help="Delete pipeline")
    delete_pipeline_parser.add_argument("pipeline_id", help="Pipeline ID")
    delete_pipeline_parser.add_argument("--force", action="store_true", help="Force deletion without confirmation")

    # Test pipeline
    test_pipeline_parser = pipelines_subparsers.add_parser("test", help="Test pipeline")
    test_pipeline_parser.add_argument("pipeline_id", help="Pipeline ID")
    test_pipeline_parser.add_argument("test_query", help="Test query")
    test_pipeline_parser.add_argument("--verbose", action="store_true", help="Include detailed test results")
    test_pipeline_parser.add_argument("--save-results", action="store_true", help="Save test results for analysis")


def main_cli(args: Sequence[str] | None = None) -> CLIResult:
    """Main CLI entry point.

    Args:
        args: Command line arguments (None to use sys.argv)

    Returns:
        CLIResult with exit code and output
    """
    parser = create_main_parser()

    try:
        # Parse arguments
        if args is None:
            args = sys.argv[1:]

        parsed_args = parser.parse_args(args)

        # Handle case where no command is specified
        if not parsed_args.command:
            parser.print_help()
            return CLIResult(exit_code=1, output="No command specified")

        # Create configuration
        config = RAGConfig(
            api_url=parsed_args.api_url,
            profile=parsed_args.profile,
            timeout=parsed_args.timeout,
            output_format=parsed_args.output,
            verbose=parsed_args.verbose,
            dry_run=getattr(parsed_args, "dry_run", False),
        )

        # Execute command based on what was requested
        from rag_solution.cli.client import RAGAPIClient
        from rag_solution.cli.commands import (
            AuthCommands,
            CollectionCommands,
            ConfigCommands,
            DocumentCommands,
            HealthCommands,
            PipelineCommands,
            ProviderCommands,
            SearchCommands,
            UserCommands,
        )
        from rag_solution.cli.output import format_json_output, format_table_output, print_error, print_status

        # Create API client
        api_client = RAGAPIClient(config)

        # Route to appropriate command handler
        if parsed_args.command == "auth":
            auth_cmd = AuthCommands(api_client, config)
            if hasattr(parsed_args, "auth_command") and parsed_args.auth_command:
                if parsed_args.auth_command == "login":
                    username = getattr(parsed_args, "username", None)
                    password = getattr(parsed_args, "password", None)
                    provider = getattr(parsed_args, "provider", "local")
                    interactive = not getattr(parsed_args, "no_interactive", False)
                    result = auth_cmd.login(
                        username=username, password=password, provider=provider, interactive=interactive
                    )
                elif parsed_args.auth_command == "set-token":
                    token = getattr(parsed_args, "token", None)
                    expires_in = getattr(parsed_args, "expires_in", 86400)
                    result = auth_cmd.set_token(token=token, expires_in=expires_in)
                elif parsed_args.auth_command == "logout":
                    result = auth_cmd.logout()
                elif parsed_args.auth_command == "status":
                    result = auth_cmd.status()
                else:
                    return CLIResult(exit_code=1, error=f"Unknown auth command: {parsed_args.auth_command}")

                # Handle result
                if result.success:
                    if config.output_format == "json":
                        print(format_json_output(result.data or {}))
                    else:
                        print_status(result.message or "Success", "success")
                    return CLIResult(exit_code=0, output=result.message)
                else:
                    print_error(result.message or "Command failed")
                    return CLIResult(exit_code=1, error=result.message)
            else:
                return CLIResult(
                    exit_code=1, error="No auth command specified. Use: login, set-token, logout, or status"
                )

        elif parsed_args.command == "collections":
            collections_cmd = CollectionCommands(api_client, config)
            if hasattr(parsed_args, "collections_command") and parsed_args.collections_command:
                if parsed_args.collections_command == "list":
                    result = collections_cmd.list_collections(
                        private_only=getattr(parsed_args, "private", False),
                        shared_only=getattr(parsed_args, "shared", False),
                        team=getattr(parsed_args, "team", None),
                    )
                elif parsed_args.collections_command == "create":
                    result = collections_cmd.create_collection(
                        name=parsed_args.name,
                        description=getattr(parsed_args, "description", None),
                        vector_db=getattr(parsed_args, "vector_db", "milvus"),
                        is_private=getattr(parsed_args, "private", False),
                    )
                elif parsed_args.collections_command == "get":
                    result = collections_cmd.get_collection(
                        collection_id=parsed_args.collection_id, include_stats=getattr(parsed_args, "stats", False)
                    )
                else:
                    return CLIResult(
                        exit_code=1, error=f"Unknown collections command: {parsed_args.collections_command}"
                    )

                # Handle result
                if result.success:
                    if config.output_format == "json":
                        print(format_json_output(result.data or {}))
                    elif config.output_format == "table" and result.data:
                        if isinstance(result.data, list):
                            print(format_table_output(result.data))
                        elif isinstance(result.data, dict) and "items" in result.data:
                            print(format_table_output(result.data["items"]))
                        else:
                            print(format_json_output(result.data))
                    else:
                        print_status(result.message or "Success", "success")
                    return CLIResult(exit_code=0, output=result.message)
                else:
                    print_error(result.message or "Command failed")
                    return CLIResult(exit_code=1, error=result.message)
            else:
                return CLIResult(exit_code=1, error="No collections command specified. Use: list, create, or get")

        elif parsed_args.command == "users":
            users_cmd = UserCommands(api_client, config)
            if hasattr(parsed_args, "users_command") and parsed_args.users_command:
                if parsed_args.users_command == "list":
                    result = users_cmd.list_users(
                        role=getattr(parsed_args, "role", None),
                        team=getattr(parsed_args, "team", None),
                        active_only=getattr(parsed_args, "active", False),
                    )
                elif parsed_args.users_command == "create":
                    result = users_cmd.create_user(
                        email=parsed_args.email,
                        name=parsed_args.name,
                        role=getattr(parsed_args, "role", "user"),
                        teams=getattr(parsed_args, "teams", None),
                    )
                elif parsed_args.users_command == "show":
                    result = users_cmd.get_user(parsed_args.user_id)
                elif parsed_args.users_command == "update":
                    result = users_cmd.update_user(
                        user_id=parsed_args.user_id,
                        name=getattr(parsed_args, "name", None),
                        role=getattr(parsed_args, "role", None),
                        active=getattr(parsed_args, "active", None),
                    )
                elif parsed_args.users_command == "delete":
                    result = users_cmd.delete_user(
                        user_id=parsed_args.user_id,
                        force=getattr(parsed_args, "force", False),
                    )
                else:
                    return CLIResult(exit_code=1, error=f"Unknown users command: {parsed_args.users_command}")

                # Handle result
                if result.success:
                    if config.output_format == "json":
                        print(format_json_output(result.data or {}))
                    elif config.output_format == "table" and result.data:
                        if isinstance(result.data, list):
                            print(format_table_output(result.data))
                        elif isinstance(result.data, dict) and "items" in result.data:
                            print(format_table_output(result.data["items"]))
                        else:
                            print(format_json_output(result.data))
                    else:
                        print_status(result.message or "Success", "success")
                    return CLIResult(exit_code=0, output=result.message)
                else:
                    print_error(result.message or "Command failed")
                    return CLIResult(exit_code=1, error=result.message)
            else:
                return CLIResult(
                    exit_code=1, error="No users command specified. Use: list, create, show, update, or delete"
                )

        elif parsed_args.command == "documents":
            documents_cmd = DocumentCommands(api_client, config)
            if hasattr(parsed_args, "documents_command") and parsed_args.documents_command:
                if parsed_args.documents_command == "upload":
                    result = documents_cmd.upload_document(
                        file_path=parsed_args.file_path,
                        collection_id=parsed_args.collection_id,
                        metadata=getattr(parsed_args, "metadata", None),
                    )
                elif parsed_args.documents_command == "list":
                    result = documents_cmd.list_documents(
                        collection_id=parsed_args.collection_id,
                        status=getattr(parsed_args, "status", None),
                    )
                elif parsed_args.documents_command == "show":
                    result = documents_cmd.get_document(parsed_args.document_id)
                elif parsed_args.documents_command == "delete":
                    result = documents_cmd.delete_document(
                        document_id=parsed_args.document_id,
                        force=getattr(parsed_args, "force", False),
                    )
                elif parsed_args.documents_command == "batch-upload":
                    # TODO: Implement batch upload
                    result = documents_cmd._create_error_result(
                        message="Batch upload not yet implemented", error_code="NOT_IMPLEMENTED"
                    )
                else:
                    return CLIResult(exit_code=1, error=f"Unknown documents command: {parsed_args.documents_command}")

                # Handle result
                if result.success:
                    if config.output_format == "json":
                        print(format_json_output(result.data or {}))
                    elif config.output_format == "table" and result.data:
                        if isinstance(result.data, list):
                            print(format_table_output(result.data))
                        elif isinstance(result.data, dict) and "items" in result.data:
                            print(format_table_output(result.data["items"]))
                        else:
                            print(format_json_output(result.data))
                    else:
                        print_status(result.message or "Success", "success")
                    return CLIResult(exit_code=0, output=result.message)
                else:
                    print_error(result.message or "Command failed")
                    return CLIResult(exit_code=1, error=result.message)
            else:
                return CLIResult(
                    exit_code=1,
                    error="No documents command specified. Use: upload, list, show, delete, or batch-upload",
                )

        elif parsed_args.command == "search":
            search_cmd = SearchCommands(api_client, config)
            if hasattr(parsed_args, "search_command") and parsed_args.search_command:
                if parsed_args.search_command == "query":
                    result = search_cmd.query(
                        collection_id=parsed_args.collection_id,
                        query=parsed_args.query,
                        pipeline_id=getattr(parsed_args, "pipeline_id", None),
                        max_chunks=getattr(parsed_args, "max_chunks", 5),
                    )
                elif parsed_args.search_command == "explain":
                    result = search_cmd.explain(
                        collection_id=parsed_args.collection_id,
                        query=parsed_args.query,
                        show_retrieval=getattr(parsed_args, "show_retrieval", False),
                        show_rewriting=getattr(parsed_args, "show_rewriting", False),
                    )
                elif parsed_args.search_command == "batch":
                    # TODO: Implement batch search
                    result = search_cmd._create_error_result(
                        message="Batch search not yet implemented", error_code="NOT_IMPLEMENTED"
                    )
                else:
                    return CLIResult(exit_code=1, error=f"Unknown search command: {parsed_args.search_command}")

                # Handle result
                if result.success:
                    if config.output_format == "json":
                        print(format_json_output(result.data or {}))
                    elif config.output_format == "table" and result.data:
                        if isinstance(result.data, list):
                            print(format_table_output(result.data))
                        elif isinstance(result.data, dict) and "items" in result.data:
                            print(format_table_output(result.data["items"]))
                        else:
                            print(format_json_output(result.data))
                    else:
                        print_status(result.message or "Success", "success")
                    return CLIResult(exit_code=0, output=result.message)
                else:
                    print_error(result.message or "Command failed")
                    return CLIResult(exit_code=1, error=result.message)
            else:
                return CLIResult(exit_code=1, error="No search command specified. Use: query, explain, or batch")

        elif parsed_args.command == "health":
            health_cmd = HealthCommands(api_client, config)
            if hasattr(parsed_args, "health_command") and parsed_args.health_command:
                if parsed_args.health_command == "check":
                    # Run multiple health checks based on flags
                    results = []
                    if getattr(parsed_args, "api", False):
                        results.append(health_cmd.check_health())
                    if getattr(parsed_args, "database", False):
                        results.append(health_cmd.check_database_health())
                    if getattr(parsed_args, "vector_db", False):
                        results.append(health_cmd.check_vector_db_health())

                    # If no specific checks requested, run general health check
                    if not results:
                        results.append(health_cmd.check_health())

                    # Return combined result
                    all_success = all(r.success for r in results)
                    combined_data = {"checks": [r.data for r in results]}
                    message = "All health checks passed" if all_success else "Some health checks failed"

                    result = (
                        health_cmd._create_success_result(data=combined_data, message=message)
                        if all_success
                        else health_cmd._create_error_result(message=message, data=combined_data)
                    )
                else:
                    return CLIResult(exit_code=1, error=f"Unknown health command: {parsed_args.health_command}")

                # Handle result
                if result.success:
                    if config.output_format == "json":
                        print(format_json_output(result.data or {}))
                    elif config.output_format == "table" and result.data:
                        if isinstance(result.data, list):
                            print(format_table_output(result.data))
                        elif isinstance(result.data, dict) and "items" in result.data:
                            print(format_table_output(result.data["items"]))
                        else:
                            print(format_json_output(result.data))
                    else:
                        print_status(result.message or "Success", "success")
                    return CLIResult(exit_code=0, output=result.message)
                else:
                    print_error(result.message or "Command failed")
                    return CLIResult(exit_code=1, error=result.message)
            else:
                return CLIResult(exit_code=1, error="No health command specified. Use: check")

        elif parsed_args.command == "config":
            config_cmd = ConfigCommands(api_client, config)
            if hasattr(parsed_args, "config_command") and parsed_args.config_command:
                if parsed_args.config_command == "show":
                    result = config_cmd.get_current_profile()
                elif parsed_args.config_command == "validate":
                    # TODO: Implement config validation
                    result = config_cmd._create_error_result(
                        message="Config validation not yet implemented", error_code="NOT_IMPLEMENTED"
                    )
                elif parsed_args.config_command == "reset":
                    # TODO: Implement config reset
                    result = config_cmd._create_error_result(
                        message="Config reset not yet implemented", error_code="NOT_IMPLEMENTED"
                    )
                else:
                    return CLIResult(exit_code=1, error=f"Unknown config command: {parsed_args.config_command}")

                # Handle result
                if result.success:
                    if config.output_format == "json":
                        print(format_json_output(result.data or {}))
                    elif config.output_format == "table" and result.data:
                        if isinstance(result.data, list):
                            print(format_table_output(result.data))
                        elif isinstance(result.data, dict) and "items" in result.data:
                            print(format_table_output(result.data["items"]))
                        else:
                            print(format_json_output(result.data))
                    else:
                        print_status(result.message or "Success", "success")
                    return CLIResult(exit_code=0, output=result.message)
                else:
                    print_error(result.message or "Command failed")
                    return CLIResult(exit_code=1, error=result.message)
            else:
                return CLIResult(exit_code=1, error="No config command specified. Use: show, validate, or reset")

        elif parsed_args.command == "providers":
            providers_cmd = ProviderCommands(api_client, config)
            if hasattr(parsed_args, "providers_command") and parsed_args.providers_command:
                if parsed_args.providers_command == "list":
                    result = providers_cmd.list_providers()
                elif parsed_args.providers_command == "create":
                    result = providers_cmd.create_provider(
                        name=parsed_args.name,
                        provider_type=parsed_args.type,
                        api_key=getattr(parsed_args, "api_key", None),
                        endpoint=getattr(parsed_args, "endpoint", None),
                        model=getattr(parsed_args, "model", None),
                    )
                elif parsed_args.providers_command == "show":
                    result = providers_cmd.get_provider(parsed_args.provider_id)
                elif parsed_args.providers_command == "update":
                    result = providers_cmd.update_provider(
                        provider_id=parsed_args.provider_id,
                        api_key=getattr(parsed_args, "api_key", None),
                        endpoint=getattr(parsed_args, "endpoint", None),
                        model=getattr(parsed_args, "model", None),
                    )
                elif parsed_args.providers_command == "delete":
                    result = providers_cmd.delete_provider(
                        provider_id=parsed_args.provider_id,
                        force=getattr(parsed_args, "force", False),
                        migrate_pipelines_to=getattr(parsed_args, "migrate_pipelines_to", None),
                    )
                elif parsed_args.providers_command == "test":
                    result = providers_cmd.test_provider(
                        provider_id=parsed_args.provider_id,
                        test_query=getattr(parsed_args, "query", None),
                        verbose=getattr(parsed_args, "verbose", False),
                    )
                else:
                    return CLIResult(exit_code=1, error=f"Unknown providers command: {parsed_args.providers_command}")

                # Handle result
                if result.success:
                    if config.output_format == "json":
                        print(format_json_output(result.data or {}))
                    elif config.output_format == "table" and result.data:
                        if isinstance(result.data, list):
                            print(format_table_output(result.data))
                        elif isinstance(result.data, dict) and "items" in result.data:
                            print(format_table_output(result.data["items"]))
                        else:
                            print(format_json_output(result.data))
                    else:
                        print_status(result.message or "Success", "success")
                    return CLIResult(exit_code=0, output=result.message)
                else:
                    print_error(result.message or "Command failed")
                    return CLIResult(exit_code=1, error=result.message)
            else:
                return CLIResult(
                    exit_code=1,
                    error="No providers command specified. Use: list, create, show, update, delete, or test",
                )

        elif parsed_args.command == "pipelines":
            pipelines_cmd = PipelineCommands(api_client, config)
            if hasattr(parsed_args, "pipelines_command") and parsed_args.pipelines_command:
                if parsed_args.pipelines_command == "list":
                    result = pipelines_cmd.list_pipelines()
                elif parsed_args.pipelines_command == "create":
                    # Parse parameters if provided
                    parameters = None
                    if hasattr(parsed_args, "parameters") and parsed_args.parameters:
                        import json

                        try:
                            parameters = json.loads(parsed_args.parameters)
                        except json.JSONDecodeError:
                            return CLIResult(exit_code=1, error="Invalid JSON in parameters")

                    result = pipelines_cmd.create_pipeline(
                        name=parsed_args.name,
                        llm_provider_id=getattr(parsed_args, "llm_provider", None),
                        parameters=parameters,
                        template_id=getattr(parsed_args, "template", None),
                    )
                elif parsed_args.pipelines_command == "show":
                    result = pipelines_cmd.get_pipeline(
                        pipeline_id=parsed_args.pipeline_id,
                        include_config=getattr(parsed_args, "include_config", False),
                        include_performance=getattr(parsed_args, "include_performance", False),
                    )
                elif parsed_args.pipelines_command == "update":
                    # Parse parameters if provided
                    parameters = None
                    if hasattr(parsed_args, "parameters") and parsed_args.parameters:
                        import json

                        try:
                            parameters = json.loads(parsed_args.parameters)
                        except json.JSONDecodeError:
                            return CLIResult(exit_code=1, error="Invalid JSON in parameters")

                    result = pipelines_cmd.update_pipeline(
                        pipeline_id=parsed_args.pipeline_id,
                        provider_id=getattr(parsed_args, "provider", None),
                        parameters=parameters,
                    )
                elif parsed_args.pipelines_command == "delete":
                    result = pipelines_cmd.delete_pipeline(
                        pipeline_id=parsed_args.pipeline_id,
                        force=getattr(parsed_args, "force", False),
                    )
                elif parsed_args.pipelines_command == "test":
                    result = pipelines_cmd.test_pipeline(
                        pipeline_id=parsed_args.pipeline_id,
                        test_query=parsed_args.test_query,
                        verbose=getattr(parsed_args, "verbose", False),
                        save_results=getattr(parsed_args, "save_results", False),
                    )
                else:
                    return CLIResult(exit_code=1, error=f"Unknown pipelines command: {parsed_args.pipelines_command}")

                # Handle result
                if result.success:
                    if config.output_format == "json":
                        print(format_json_output(result.data or {}))
                    elif config.output_format == "table" and result.data:
                        if isinstance(result.data, list):
                            print(format_table_output(result.data))
                        elif isinstance(result.data, dict) and "items" in result.data:
                            print(format_table_output(result.data["items"]))
                        else:
                            print(format_json_output(result.data))
                    else:
                        print_status(result.message or "Success", "success")
                    return CLIResult(exit_code=0, output=result.message)
                else:
                    print_error(result.message or "Command failed")
                    return CLIResult(exit_code=1, error=result.message)
            else:
                return CLIResult(
                    exit_code=1,
                    error="No pipelines command specified. Use: list, create, show, update, delete, or test",
                )

        # Add more command handlers as needed...
        else:
            output = f"Command '{parsed_args.command}' is not yet implemented"
            print_status(output, "warning")
            return CLIResult(exit_code=0, output=output)

    except KeyboardInterrupt:
        print_status("Operation cancelled by user", "warning")
        return CLIResult(exit_code=130, error="Operation cancelled")
    except RAGCLIError as e:
        print_error(str(e))
        return CLIResult(exit_code=1, error=str(e))
    except Exception as e:
        print_error(f"Unexpected error: {e!s}")
        return CLIResult(exit_code=2, error=str(e))


def main() -> None:
    """Main entry point for the rag-cli command."""
    result = main_cli()
    sys.exit(result.exit_code)


if __name__ == "__main__":
    main()
