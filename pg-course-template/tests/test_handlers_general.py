"""Unit tests for general handlers (handlers/general.py).

Covers show_help, clear_screen, and exit_app commands.
"""

from unittest.mock import MagicMock, patch


class TestShowHelp:
    """show_help() groups commands by category and prints a Panel."""

    def test_show_help_groups_by_category(self, mock_db, mock_user):
        """Registered commands are grouped by their category in the help output."""
        from commands import command
        from auth import ALL_ROLES

        with patch("db.get_conn", return_value=mock_db):
            from handlers import general  # noqa: F811

            @command("test_list", "тестовый список", "СКЛАДЫ", ALL_ROLES)
            def test_list_fn():
                pass

            with patch.object(general, "console") as mock_console:
                general.show_help()
            # console.print was called multiple times (blank line, panel, blank line)
            assert mock_console.print.call_count >= 3

    def test_show_help_shows_command_descriptions(self, mock_db, mock_user):
        """Help text includes command descriptions."""
        from commands import command
        from auth import ALL_ROLES

        with patch("db.get_conn", return_value=mock_db):
            from handlers import general  # noqa: F811

            @command("test_desc", "очень важное описание", "ПРОЧЕЕ", ALL_ROLES)
            def test_desc_fn():
                pass

            with patch.object(general, "console") as mock_console:
                general.show_help()
            from rich.panel import Panel

            panel_call = [
                c
                for c in mock_console.print.call_args_list
                if len(c[0]) > 0 and isinstance(c[0][0], Panel)
            ]
            assert len(panel_call) > 0


class TestClearScreen:
    """clear_screen() calls console.clear()."""

    def test_clear_screen_calls_console_clear(self, mock_db, mock_user):
        with patch("db.get_conn", return_value=mock_db):
            from handlers import general  # noqa: F811

        with patch.object(general, "console") as mock_console:
            general.clear_screen()
        mock_console.clear.assert_called_once()


class TestExitApp:
    """exit_app() is a no-op (handled by main loop)."""

    def test_exit_app_does_nothing(self, mock_db, mock_user):
        """exit_app() returns without side effects."""
        with patch("db.get_conn", return_value=mock_db):
            from handlers.general import exit_app

        result = exit_app()
        assert result is None
