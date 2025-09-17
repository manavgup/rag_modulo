"""Administrative CLI for RAG Modulo.

This module provides a focused CLI interface for administrative operations,
including user management, system configuration, and maintenance tasks.
"""

import argparse
import sys
from collections.abc import Sequence

from .client import RAGAPIClient
from .commands.config import ConfigCommands
from .commands.health import HealthCommands
from .commands.users import UserCommands
from .config import RAGConfig
from .output import format_json_output, format_table_output, print_error, print_status


def create_admin_parser() -> argparse.ArgumentParser:
    """Create the admin CLI argument parser.

    Returns:
        Configured ArgumentParser instance for admin operations
    """
    parser = argparse.ArgumentParser(
        prog="rag-admin",
        description="RAG Modulo - Administrative Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  rag-admin users create user@example.com --name "John Doe" --role admin
  rag-admin users list --role admin --active
  rag-admin health check --api --database --vector-db
  rag-admin config validate --api-url http://localhost:8000
        """,
    )

    # Global options
    parser.add_argument("--profile", default="default", help="Configuration profile to use")
    parser.add_argument("--api-url", default="http://localhost:8000", help="RAG Modulo API base URL")
    parser.add_argument("--timeout", type=int, default=30, help="Request timeout in seconds")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--output", "-o", choices=["table", "json", "yaml"], default="table", help="Output format")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")

    # Create subparsers for admin commands
    subparsers = parser.add_subparsers(
        dest="command",
        title="Admin Commands",
        description="Use 'rag-admin <command> --help' for command-specific help",
        help="Admin command to execute",
    )

    # User management commands
    _add_user_admin_commands(subparsers)

    # Health check commands
    _add_health_admin_commands(subparsers)

    # Configuration commands
    _add_config_admin_commands(subparsers)

    return parser


def _add_user_admin_commands(subparsers: argparse._SubParsersAction) -> None:
    """Add user management admin commands.

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

    # Batch operations
    batch_users_parser = users_subparsers.add_parser("batch", help="Batch user operations")
    batch_users_subparsers = batch_users_parser.add_subparsers(dest="batch_command", help="Batch commands")

    # Import users
    import_users_parser = batch_users_subparsers.add_parser("import", help="Import users from file")
    import_users_parser.add_argument("file_path", help="Path to users data file (JSON)")
    import_users_parser.add_argument(
        "--conflict-resolution", default="skip", choices=["skip", "update", "error"], help="How to handle conflicts"
    )

    # Export users
    export_users_parser = batch_users_subparsers.add_parser("export", help="Export users to file")
    export_users_parser.add_argument("--output", help="Output file path")
    export_users_parser.add_argument("--include-inactive", action="store_true", help="Include inactive users")


def _add_health_admin_commands(subparsers: argparse._SubParsersAction) -> None:
    """Add health check admin commands.

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
    check_parser.add_argument("--llm-providers", action="store_true", help="Check LLM providers health")
    check_parser.add_argument("--timeout", type=int, default=30, help="Health check timeout")

    # Diagnostics
    diagnostics_parser = health_subparsers.add_parser("diagnostics", help="Run system diagnostics")
    diagnostics_parser.add_argument("--component", help="Specific component to diagnose")
    diagnostics_parser.add_argument("--verbose", action="store_true", help="Include verbose diagnostic information")

    # Metrics
    metrics_parser = health_subparsers.add_parser("metrics", help="Get system metrics")
    metrics_parser.add_argument("--type", help="Metric type filter")
    metrics_parser.add_argument("--time-range", default="1h", help="Time range for metrics")

    # Version info
    health_subparsers.add_parser("version", help="Get version information")


def _add_config_admin_commands(subparsers: argparse._SubParsersAction) -> None:
    """Add configuration admin commands.

    Args:
        subparsers: Subparsers action from main parser
    """
    config_parser = subparsers.add_parser(
        "config", help="Configuration management", description="Manage system configuration"
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


def main_admin_cli(args: Sequence[str] | None = None) -> int:
    """Main admin CLI entry point.

    Args:
        args: Command line arguments (None to use sys.argv)

    Returns:
        Exit code (0 for success)
    """
    parser = create_admin_parser()

    try:
        # Parse arguments
        if args is None:
            args = sys.argv[1:]

        parsed_args = parser.parse_args(args)

        # Handle case where no command is specified
        if not parsed_args.command:
            parser.print_help()
            return 1

        # Create configuration
        config = RAGConfig(
            api_url=parsed_args.api_url,
            profile=parsed_args.profile,
            timeout=parsed_args.timeout,
            output_format=parsed_args.output,
            verbose=parsed_args.verbose,
        )

        # Create API client
        api_client = RAGAPIClient(config)

        # Route to appropriate command handler
        if parsed_args.command == "users":
            users_cmd = UserCommands(api_client, config)
            result = _handle_user_admin_command(users_cmd, parsed_args)
        elif parsed_args.command == "health":
            health_cmd = HealthCommands(api_client, config)
            result = _handle_health_admin_command(health_cmd, parsed_args)
        elif parsed_args.command == "config":
            config_cmd = ConfigCommands(api_client, config)
            result = _handle_config_admin_command(config_cmd, parsed_args)
        else:
            print_error(f"Unknown admin command: {parsed_args.command}")
            return 1

        # Handle result
        if hasattr(result, "success") and result.success:
            if config.output_format == "json":
                print(format_json_output(getattr(result, "data", None) or {}))
            elif config.output_format == "table" and hasattr(result, "data") and result.data:
                if isinstance(result.data, list):
                    print(format_table_output(result.data))
                elif isinstance(result.data, dict) and "items" in result.data:
                    print(format_table_output(result.data["items"]))
                else:
                    print(format_json_output(result.data))
            else:
                print_status(getattr(result, "message", None) or "Command completed successfully", "success")
            return 0
        print_error(getattr(result, "message", None) or "Command failed")
        return 1

    except KeyboardInterrupt:
        print_status("Operation cancelled by user", "warning")
        return 130
    except (ConnectionError, ValueError, TypeError, AttributeError) as e:
        print_error(f"Admin error: {e!s}")
        return 2


def _handle_batch_user_command(users_cmd: UserCommands, args) -> object:
    """Handle batch user commands.

    Args:
        users_cmd: UserCommands instance
        args: Parsed arguments

    Returns:
        CommandResult
    """
    if args.batch_command == "import":
        return users_cmd.create_error_result(message="User import not yet implemented", error_code="NOT_IMPLEMENTED")
    if args.batch_command == "export":
        return users_cmd.create_error_result(message="User export not yet implemented", error_code="NOT_IMPLEMENTED")
    return users_cmd.create_error_result(
        message=f"Unknown batch command: {args.batch_command}", error_code="UNKNOWN_COMMAND"
    )


def _handle_health_check_command(health_cmd: HealthCommands, args) -> object:
    """Handle health check command.

    Args:
        health_cmd: HealthCommands instance
        args: Parsed arguments

    Returns:
        CommandResult
    """
    # Run multiple health checks based on flags
    results = []
    if getattr(args, "api", False):
        results.append(health_cmd.check_health())
    if getattr(args, "database", False):
        results.append(health_cmd.check_database_health())
    if getattr(args, "vector_db", False):
        results.append(health_cmd.check_vector_db_health())
    if getattr(args, "llm_providers", False):
        results.append(health_cmd.check_llm_providers_health())

    # If no specific checks requested, run general health check
    if not results:
        results.append(health_cmd.check_health())

    # Return combined result
    all_success = all(r.success for r in results)
    combined_data = {"checks": [r.data for r in results]}
    message = "All health checks passed" if all_success else "Some health checks failed"

    return (
        health_cmd.create_success_result(data=combined_data, message=message)
        if all_success
        else health_cmd.create_error_result(message=message, data=combined_data)
    )


def _handle_user_admin_command(users_cmd: UserCommands, args) -> object:
    """Handle user admin commands.

    Args:
        users_cmd: UserCommands instance
        args: Parsed arguments

    Returns:
        CommandResult
    """
    if args.users_command == "list":
        return users_cmd.list_users(
            role=getattr(args, "role", None),
            team=getattr(args, "team", None),
            active_only=getattr(args, "active", False),
        )
    if args.users_command == "create":
        return users_cmd.create_user(
            email=args.email,
            name=args.name,
            role=getattr(args, "role", "user"),
            teams=getattr(args, "teams", None),
        )
    if args.users_command == "show":
        return users_cmd.get_user(args.user_id)
    if args.users_command == "update":
        return users_cmd.update_user(
            user_id=args.user_id,
            name=getattr(args, "name", None),
            role=getattr(args, "role", None),
            active=getattr(args, "active", None),
        )
    if args.users_command == "delete":
        return users_cmd.delete_user(
            user_id=args.user_id,
            force=getattr(args, "force", False),
        )
    if args.users_command == "batch":
        return _handle_batch_user_command(users_cmd, args)
    return users_cmd.create_error_result(
        message=f"Unknown users command: {args.users_command}", error_code="UNKNOWN_COMMAND"
    )


def _handle_health_admin_command(health_cmd: HealthCommands, args) -> object:
    """Handle health admin commands.

    Args:
        health_cmd: HealthCommands instance
        args: Parsed arguments

    Returns:
        CommandResult
    """
    if args.health_command == "check":
        return _handle_health_check_command(health_cmd, args)
    if args.health_command == "diagnostics":
        return health_cmd.run_diagnostics(
            component=getattr(args, "component", None),
            verbose=getattr(args, "verbose", False),
        )
    if args.health_command == "metrics":
        return health_cmd.get_metrics(metric_type=getattr(args, "type", None))
    if args.health_command == "version":
        return health_cmd.get_version_info()
    return health_cmd.create_error_result(
        message=f"Unknown health command: {args.health_command}", error_code="UNKNOWN_COMMAND"
    )


def _handle_config_admin_command(config_cmd: ConfigCommands, args) -> object:
    """Handle config admin commands.

    Args:
        config_cmd: ConfigCommands instance
        args: Parsed arguments

    Returns:
        CommandResult
    """
    if args.config_command == "show":
        return config_cmd.get_current_profile()
    if args.config_command == "validate":
        return config_cmd.create_error_result(
            message="Config validation not yet implemented", error_code="NOT_IMPLEMENTED"
        )
    if args.config_command == "reset":
        return config_cmd.create_error_result(message="Config reset not yet implemented", error_code="NOT_IMPLEMENTED")
    return config_cmd.create_error_result(
        message=f"Unknown config command: {args.config_command}", error_code="UNKNOWN_COMMAND"
    )


def main() -> None:
    """Main entry point for the rag-admin command."""
    sys.exit(main_admin_cli())


if __name__ == "__main__":
    main()
