"""Unit tests for MCP server CLI entry point.

Tests for __main__.py command-line interface.
"""

from io import StringIO
from unittest.mock import patch

import pytest


class TestMainEntryPoint:
    """Tests for the main entry point."""

    def test_main_default_transport(self) -> None:
        """Test main function with default transport (stdio)."""
        with patch("backend.mcp_server.__main__.run_server") as mock_run, patch("sys.argv", ["mcp_server"]):
            from backend.mcp_server.__main__ import main

            main()

            mock_run.assert_called_once_with(transport="stdio", port=8080)

    def test_main_sse_transport(self) -> None:
        """Test main function with SSE transport."""
        with (
            patch("backend.mcp_server.__main__.run_server") as mock_run,
            patch("sys.argv", ["mcp_server", "--transport", "sse"]),
        ):
            from backend.mcp_server.__main__ import main

            main()

            mock_run.assert_called_once_with(transport="sse", port=8080)

    def test_main_http_transport(self) -> None:
        """Test main function with HTTP transport."""
        with (
            patch("backend.mcp_server.__main__.run_server") as mock_run,
            patch("sys.argv", ["mcp_server", "--transport", "http"]),
        ):
            from backend.mcp_server.__main__ import main

            main()

            mock_run.assert_called_once_with(transport="http", port=8080)

    def test_main_custom_port(self) -> None:
        """Test main function with custom port."""
        with (
            patch("backend.mcp_server.__main__.run_server") as mock_run,
            patch("sys.argv", ["mcp_server", "--port", "9000"]),
        ):
            from backend.mcp_server.__main__ import main

            main()

            mock_run.assert_called_once_with(transport="stdio", port=9000)

    def test_main_sse_with_custom_port(self) -> None:
        """Test main function with SSE transport and custom port."""
        with (
            patch("backend.mcp_server.__main__.run_server") as mock_run,
            patch("sys.argv", ["mcp_server", "--transport", "sse", "--port", "3000"]),
        ):
            from backend.mcp_server.__main__ import main

            main()

            mock_run.assert_called_once_with(transport="sse", port=3000)

    def test_main_log_level_debug(self) -> None:
        """Test main function with DEBUG log level."""
        with (
            patch("backend.mcp_server.__main__.run_server"),
            patch("sys.argv", ["mcp_server", "--log-level", "DEBUG"]),
            patch("logging.basicConfig") as mock_logging,
        ):
            import logging

            from backend.mcp_server.__main__ import main

            main()

            # Verify logging was configured with DEBUG level
            mock_logging.assert_called_once()
            call_kwargs = mock_logging.call_args[1]
            assert call_kwargs["level"] == logging.DEBUG

    def test_main_log_level_warning(self) -> None:
        """Test main function with WARNING log level."""
        with (
            patch("backend.mcp_server.__main__.run_server"),
            patch("sys.argv", ["mcp_server", "--log-level", "WARNING"]),
            patch("logging.basicConfig") as mock_logging,
        ):
            import logging

            from backend.mcp_server.__main__ import main

            main()

            mock_logging.assert_called_once()
            call_kwargs = mock_logging.call_args[1]
            assert call_kwargs["level"] == logging.WARNING

    def test_main_keyboard_interrupt(self) -> None:
        """Test main function handles KeyboardInterrupt."""
        with (
            patch("backend.mcp_server.__main__.run_server", side_effect=KeyboardInterrupt()),
            patch("sys.argv", ["mcp_server"]),
        ):
            from backend.mcp_server.__main__ import main

            # Should not raise, just log and exit gracefully
            main()

    def test_main_exception_exits_with_error(self) -> None:
        """Test main function exits with error code on exception."""
        with (
            patch(
                "backend.mcp_server.__main__.run_server",
                side_effect=Exception("Test error"),
            ),
            patch("sys.argv", ["mcp_server"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            from backend.mcp_server.__main__ import main

            main()

            assert exc_info.value.code == 1

    def test_main_invalid_transport(self) -> None:
        """Test main function with invalid transport."""
        with (
            patch("sys.argv", ["mcp_server", "--transport", "invalid"]),
            patch("sys.stderr", new_callable=StringIO),
            pytest.raises(SystemExit) as exc_info,
        ):
            from backend.mcp_server.__main__ import main

            main()

            assert exc_info.value.code != 0

    def test_main_invalid_log_level(self) -> None:
        """Test main function with invalid log level."""
        with (
            patch("sys.argv", ["mcp_server", "--log-level", "INVALID"]),
            patch("sys.stderr", new_callable=StringIO),
            pytest.raises(SystemExit) as exc_info,
        ):
            from backend.mcp_server.__main__ import main

            main()

            assert exc_info.value.code != 0


class TestArgumentParser:
    """Tests for argument parser configuration."""

    def test_parser_help(self) -> None:
        """Test parser generates help text."""
        with (
            patch("sys.argv", ["mcp_server", "--help"]),
            patch("sys.stdout", new_callable=StringIO) as mock_stdout,
            pytest.raises(SystemExit) as exc_info,
        ):
            from backend.mcp_server.__main__ import main

            main()

            assert exc_info.value.code == 0
            output = mock_stdout.getvalue()
            assert "RAG Modulo MCP Server" in output or "transport" in output

    def test_parser_transport_choices(self) -> None:
        """Test parser validates transport choices."""
        from backend.mcp_server.__main__ import main

        # This should be validated by argparse
        with (
            patch("sys.argv", ["mcp_server", "--transport", "websocket"]),
            patch("sys.stderr", new_callable=StringIO),
            pytest.raises(SystemExit),
        ):
            main()

    def test_parser_port_type(self) -> None:
        """Test parser validates port is integer."""
        with (
            patch("sys.argv", ["mcp_server", "--port", "not-a-number"]),
            patch("sys.stderr", new_callable=StringIO),
            pytest.raises(SystemExit),
        ):
            from backend.mcp_server.__main__ import main

            main()


class TestModuleExecution:
    """Tests for module execution."""

    def test_module_has_main_guard(self) -> None:
        """Test module has if __name__ == '__main__' guard."""
        import inspect

        import backend.mcp_server.__main__ as main_module

        source = inspect.getsource(main_module)
        assert 'if __name__ == "__main__"' in source

    def test_main_function_exists(self) -> None:
        """Test main function is defined."""
        from backend.mcp_server.__main__ import main

        assert callable(main)
