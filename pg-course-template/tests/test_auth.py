"""Unit tests for the authentication layer (auth.py, users.py).

Uses mock DB connections — no live database required. Tests cover:
- User dataclass structure
- find_user_by_login_and_pass / get_user with mocked cursor
- auth_user() — authenticated and unauthenticated states
- login() CLI-path with mocked find_user_by_login_and_pass
- Role constants and ALL_ROLES tuple
"""

from unittest.mock import MagicMock, patch

import pytest
from users import User


class TestUserDataclass:
    """User is a simple dataclass with id, username, role."""

    def test_fields(self):
        u = User(id=1, username="alice", role="catalog_manager")
        assert u.id == 1
        assert u.username == "alice"
        assert u.role == "catalog_manager"

    def test_is_dataclass(self):
        import dataclasses

        assert dataclasses.is_dataclass(User)


class TestFindUserByLoginAndPass:
    """find_user_by_login_and_pass queries auth.users with crypt()."""

    def test_returns_user_on_valid_credentials(self, mock_db):
        """When DB row exists, a User object is returned."""
        from unittest.mock import patch as mock_patch

        mock_cursor = mock_db.cursor.return_value
        # Simulate fetchone returning a User row
        mock_cursor.execute.return_value = None
        mock_cursor.fetchone.return_value = User(
            id=2, username="bob", role="sales_manager"
        )

        with mock_patch("db.get_conn", return_value=mock_db):
            from users import find_user_by_login_and_pass

            user = find_user_by_login_and_pass("bob", "secret")
        assert user is not None
        assert user.username == "bob"
        assert user.role == "sales_manager"

    def test_returns_none_on_invalid_credentials(self, mock_db):
        """When no DB row matches, None is returned."""
        from unittest.mock import patch as mock_patch

        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = None

        with mock_patch("db.get_conn", return_value=mock_db):
            from users import find_user_by_login_and_pass

            user = find_user_by_login_and_pass("nobody", "wrong")
        assert user is None

    def test_passes_parameters_to_query(self, mock_db):
        """Username and password are passed as positional parameters."""
        from unittest.mock import patch as mock_patch

        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = None

        with mock_patch("db.get_conn", return_value=mock_db):
            from users import find_user_by_login_and_pass

            find_user_by_login_and_pass("alice", "pass123")
        call_args = mock_cursor.execute.call_args
        # First arg is the SQL, second is the parameter tuple
        assert call_args[0][1] == ("alice", "pass123")


class TestGetUser:
    """get_user looks up a single user by ID."""

    def test_returns_existing_user(self, mock_db):
        from unittest.mock import patch as mock_patch

        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = User(
            id=5, username="eve", role="worker"
        )

        with mock_patch("db.get_conn", return_value=mock_db):
            from users import get_user

            user = get_user(5)
        assert user.id == 5
        assert user.username == "eve"

    def test_returns_none_for_missing_id(self, mock_db):
        from unittest.mock import patch as mock_patch

        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = None

        with mock_patch("db.get_conn", return_value=mock_db):
            from users import get_user

            user = get_user(999)
        assert user is None


class TestAuthUser:
    """auth_user() returns the authenticated User or raises RuntimeError."""

    def test_returns_current_user(self, mock_user):
        from auth import auth_user

        user = auth_user()
        assert user.username == "test_user"

    def test_raises_when_not_authenticated(self):
        from auth import auth_user

        with pytest.raises(RuntimeError, match="Not authenticated"):
            auth_user()


class TestLogin:
    """login() authenticates via CLI args or interactive prompt."""

    def test_cli_args_success(self):
        """Valid CLI username/password sets _USER and returns password."""
        fake_user = User(id=1, username="alice", role="catalog_manager")

        with patch(
            "auth.find_user_by_login_and_pass", return_value=fake_user
        ) as mock_find:
            with patch("auth.console"):
                import auth  # noqa: F811

                result = auth.login("alice", "secret")
        assert result == "secret"
        assert auth._USER is fake_user
        mock_find.assert_called_once_with("alice", "secret")

    def test_cli_args_invalid_role_raises(self):
        """User with role not in ALL_ROLES raises ValueError."""
        rogue_user = User(id=99, username="hacker", role="unknown_role")

        with patch(
            "auth.find_user_by_login_and_pass", return_value=rogue_user
        ):
            with patch("auth.console"):
                from auth import login

                with pytest.raises(ValueError, match="Invalid user role"):
                    login("hacker", "x")

    def test_cli_args_wrong_credentials_falls_back_to_prompt(self):
        """None from find_user with CLI args prints error and enters loop."""
        fake_user = User(id=4, username="dave", role="worker")

        with patch(
            "auth.find_user_by_login_and_pass",
            side_effect=[None, fake_user],
        ):
            with patch("auth.prompt", side_effect=["dave", "right"]):
                with patch("auth.console"):
                    import auth  # noqa: F811

                    result = auth.login("dave", "wrong")
        assert result == "right"
        assert auth._USER is fake_user

    def test_interactive_login_success(self):
        """Interactive prompt loop sets _USER on valid credentials."""
        fake_user = User(id=3, username="carol", role="inventory_manager")

        with patch(
            "auth.find_user_by_login_and_pass", return_value=fake_user
        ):
            with patch("auth.prompt", side_effect=["carol", "pass"]):
                with patch("auth.console"):
                    import auth  # noqa: F811

                    auth.login()
        assert auth._USER is fake_user


class TestRoles:
    """Role constants and ALL_ROLES tuple."""

    def test_role_constants(self):
        from auth import (
            ROLE_CATALOG_MANAGER,
            ROLE_INVENTORY_MANAGER,
            ROLE_SALES_MANAGER,
            ROLE_WORKER,
        )

        assert ROLE_CATALOG_MANAGER == "catalog_manager"
        assert ROLE_SALES_MANAGER == "sales_manager"
        assert ROLE_INVENTORY_MANAGER == "inventory_manager"
        assert ROLE_WORKER == "worker"

    def test_all_roles_contains_all_four(self):
        from auth import ALL_ROLES, ROLE_CATALOG_MANAGER, ROLE_INVENTORY_MANAGER
        from auth import ROLE_SALES_MANAGER, ROLE_WORKER

        assert len(ALL_ROLES) == 4
        assert ROLE_CATALOG_MANAGER in ALL_ROLES
        assert ROLE_SALES_MANAGER in ALL_ROLES
        assert ROLE_INVENTORY_MANAGER in ALL_ROLES
        assert ROLE_WORKER in ALL_ROLES
