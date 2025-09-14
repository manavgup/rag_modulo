"""Output formatting utilities for RAG CLI.

This module provides functions for formatting CLI output in different formats
including tables, JSON, and YAML. It supports rich console output with colors
and styling.
"""

import json
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.progress import track
from rich.table import Table

try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False


class OutputFormatter:
    """Formatter for CLI output in various formats.

    This class provides methods to format data for display in the terminal,
    supporting multiple output formats and rich console features.
    """

    def __init__(self, console: Console | None = None) -> None:
        """Initialize the output formatter.

        Args:
            console: Optional Rich console instance
        """
        self.console = console or Console()

    def format_table(self, data: list[dict[str, Any]], headers: list[str] | None = None, title: str | None = None) -> str:
        """Format data as a table.

        Args:
            data: List of dictionaries to display as rows
            headers: Optional list of column headers
            title: Optional table title

        Returns:
            Formatted table string
        """
        if not data:
            return "No data to display"

        # Auto-detect headers if not provided
        if not headers:
            headers = list(data[0].keys()) if data else []

        # Create Rich table
        table = Table(title=title, show_header=True, header_style="bold magenta")

        # Add columns
        for header in headers:
            table.add_column(header.replace("_", " ").title(), style="cyan", no_wrap=False)

        # Add rows
        for row in data:
            row_values = []
            for header in headers:
                value = row.get(header, "")
                # Format value for display
                if isinstance(value, bool):
                    row_values.append("✅" if value else "❌")
                elif isinstance(value, list | dict):
                    row_values.append(json.dumps(value, default=str))
                elif value is None:
                    row_values.append("-")
                else:
                    row_values.append(str(value))
            table.add_row(*row_values)

        # Capture table output as string
        with self.console.capture() as capture:
            self.console.print(table)

        return capture.get()

    def format_json(self, data: Any, indent: int = 2) -> str:
        """Format data as JSON.

        Args:
            data: Data to format as JSON
            indent: JSON indentation level

        Returns:
            Formatted JSON string
        """
        return json.dumps(data, indent=indent, default=str, ensure_ascii=False)

    def format_yaml(self, data: Any) -> str:
        """Format data as YAML.

        Args:
            data: Data to format as YAML

        Returns:
            Formatted YAML string

        Raises:
            ImportError: If PyYAML is not installed
        """
        if not HAS_YAML:
            raise ImportError("PyYAML is required for YAML output format")

        return yaml.dump(data, default_flow_style=False, allow_unicode=True)

    def format_list(self, items: list[Any], bullet: str = "•", indent: str = "  ") -> str:  # noqa: ARG002
        """Format data as a bulleted list.

        Args:
            items: List of items to format
            bullet: Bullet character to use
            indent: Indentation string

        Returns:
            Formatted list string
        """
        if not items:
            return "No items to display"

        lines = []
        for item in items:
            if isinstance(item, dict):
                # Format dict as key-value pairs
                for key, value in item.items():
                    lines.append(f"{bullet} {key}: {value}")
            else:
                lines.append(f"{bullet} {item!s}")

        return "\n".join(lines)

    def format_key_value(self, data: dict[str, Any], separator: str = ": ") -> str:
        """Format data as key-value pairs.

        Args:
            data: Dictionary to format
            separator: Separator between key and value

        Returns:
            Formatted key-value string
        """
        lines = []
        for key, value in data.items():
            formatted_key = key.replace("_", " ").title()
            if isinstance(value, bool):
                formatted_value = "Yes" if value else "No"
            elif isinstance(value, list | dict):
                formatted_value = json.dumps(value, default=str)
            elif value is None:
                formatted_value = "None"
            else:
                formatted_value = str(value)

            lines.append(f"{formatted_key}{separator}{formatted_value}")

        return "\n".join(lines)


def format_table_output(data: list[dict[str, Any]], title: str | None = None) -> str:
    """Format data as table output (legacy function).

    Args:
        data: List of dictionaries to display
        title: Optional table title

    Returns:
        Formatted table string
    """
    formatter = OutputFormatter()
    return formatter.format_table(data, title=title)


def format_json_output(data: Any, indent: int = 2) -> str:
    """Format data as JSON output (legacy function).

    Args:
        data: Data to format
        indent: JSON indentation

    Returns:
        Formatted JSON string
    """
    formatter = OutputFormatter()
    return formatter.format_json(data, indent=indent)


def format_operation_result(message: str, success_count: int = 0, error_count: int = 0, details: dict[str, Any] | None = None) -> str:
    """Format operation result with status indicators.

    Args:
        message: Operation message
        success_count: Number of successful operations
        error_count: Number of failed operations
        details: Optional additional details

    Returns:
        Formatted result string
    """
    OutputFormatter()

    # Determine status icon
    if error_count == 0:
        status_icon = "✅"
    elif success_count > 0:
        status_icon = "⚠️"
    else:
        status_icon = "❌"

    # Build result message
    lines = [f"{status_icon} {message}"]

    if success_count > 0 and error_count > 0:
        lines.append(f"   {success_count} successful, {error_count} errors")
    elif success_count > 0:
        lines.append(f"   {success_count} items processed successfully")
    elif error_count > 0:
        lines.append(f"   {error_count} errors occurred")

    # Add details if provided
    if details:
        lines.append("\nDetails:")
        for key, value in details.items():
            lines.append(f"  {key}: {value}")

    return "\n".join(lines)


def print_status(message: str, status: str = "info") -> None:
    """Print status message with appropriate styling.

    Args:
        message: Message to print
        status: Status type (info, success, warning, error)
    """
    console = Console()

    if status == "success":
        console.print(f"✅ {message}", style="green")
    elif status == "warning":
        console.print(f"⚠️ {message}", style="yellow")
    elif status == "error":
        console.print(f"❌ {message}", style="red")
    else:
        console.print(f"i {message}", style="blue")


def print_error(error_message: str, details: str | None = None) -> None:
    """Print error message with details.

    Args:
        error_message: Main error message
        details: Optional error details
    """
    console = Console()

    console.print(f"❌ Error: {error_message}", style="red")

    if details:
        console.print(f"   Details: {details}", style="red dim")


def print_progress(items: list[Any], description: str = "Processing") -> Any:
    """Print progress bar for long-running operations.

    Args:
        items: Items to process
        description: Progress description

    Yields:
        Each item from the input list
    """
    yield from track(items, description=description)


def print_panel(content: str, title: str | None = None, border_style: str = "blue") -> None:
    """Print content in a bordered panel.

    Args:
        content: Content to display
        title: Optional panel title
        border_style: Border color/style
    """
    console = Console()
    panel = Panel(content, title=title, border_style=border_style)
    console.print(panel)


def confirm_action(message: str, default: bool = False) -> bool:
    """Prompt user for confirmation.

    Args:
        message: Confirmation message
        default: Default value if user presses enter

    Returns:
        True if user confirms, False otherwise
    """
    console = Console()

    default_text = "[Y/n]" if default else "[y/N]"
    response = console.input(f"❓ {message} {default_text}: ")

    if not response.strip():
        return default

    return response.lower() in ("y", "yes", "true", "1")


def select_from_list(items: list[str], prompt: str = "Select an option:", allow_multiple: bool = False) -> str | list[str] | None:
    """Allow user to select from a list of options.

    Args:
        items: List of options to choose from
        prompt: Selection prompt
        allow_multiple: Allow multiple selections

    Returns:
        Selected item(s) or None if cancelled
    """
    console = Console()

    if not items:
        console.print("No options available", style="yellow")
        return None

    # Display options
    console.print(prompt)
    for i, item in enumerate(items, 1):
        console.print(f"  {i}. {item}")

    if allow_multiple:
        console.print("  Enter numbers separated by commas (e.g., 1,3,5):")

    try:
        response = console.input("Enter selection: ")

        if not response.strip():
            return None

        if allow_multiple:
            # Handle multiple selections
            selections = []
            for part in response.split(","):
                try:
                    index = int(part.strip()) - 1
                    if 0 <= index < len(items):
                        selections.append(items[index])
                except ValueError:
                    continue
            return selections if selections else None
        else:
            # Handle single selection
            try:
                index = int(response.strip()) - 1
                if 0 <= index < len(items):
                    return items[index]
            except ValueError:
                pass

            return None

    except KeyboardInterrupt:
        console.print("\nSelection cancelled", style="yellow")
        return None
