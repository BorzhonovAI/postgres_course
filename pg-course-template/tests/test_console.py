"""Unit tests for the console module (console.py).

Smoke tests verifying the module exports and render_error() safety.
"""

from unittest.mock import patch

from rich.console import Console


class TestConsoleInstance:
    """console is a rich.Console instance."""

    def test_console_is_instance(self):
        from console import console

        assert isinstance(console, Console)


class TestRenderError:
    """render_error() prints a red Panel without crashing."""

    def test_render_error_does_not_crash(self):
        """Calling render_error with any message completes without exception."""
        from console import render_error

        with patch("console.console") as mock_console:
            render_error("test error message")
        mock_console.print.assert_called_once()
        # Verify a Panel was passed
        from rich.panel import Panel

        call_args = mock_console.print.call_args
        assert isinstance(call_args[0][0], Panel)

    def test_render_error_uses_red_border(self):
        """The rendered Panel has red border style."""
        from console import render_error

        with patch("console.console") as mock_console:
            render_error("another error")
        call_args = mock_console.print.call_args
        panel = call_args[0][0]
        assert panel.border_style == "red"
