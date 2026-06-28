"""Unit tests for the database connection module (db.py).

Uses mock psycopg connection — no live database required. Tests cover:
- get_conn() raises RuntimeError when not initialized
- connect() creates connection via psycopg.connect
- close() clears the connection
- get_conn() returns connection after connect
"""

from unittest.mock import MagicMock, patch

import pytest


class TestGetConnNotInitialized:
    """get_conn() raises RuntimeError when _CONN is None."""

    def test_get_conn_raises_when_not_initialized(self):
        """After reset fixture, _CONN is None, so get_conn() raises."""
        from db import get_conn

        with pytest.raises(RuntimeError, match="Database connection has not been established"):
            get_conn()


class TestConnect:
    """connect() creates a psycopg connection with the right parameters."""

    def test_connect_sets_connection(self):
        """connect() calls psycopg.connect and stores the result in _CONN."""
        mock_psycopg_connect = MagicMock(return_value=MagicMock())

        with patch("db.psycopg", MagicMock(connect=mock_psycopg_connect)):
            import db  # noqa: F811

            db.connect()
        assert db._CONN is not None
        mock_psycopg_connect.assert_called_once()
        call_kwargs = mock_psycopg_connect.call_args[1]
        assert call_kwargs["dbname"] == "inventorydb"
        assert call_kwargs["autocommit"] is True

    def test_connect_with_custom_role_and_password(self):
        """connect(role, password) passes custom credentials."""
        mock_psycopg_connect = MagicMock(return_value=MagicMock())

        with patch("db.psycopg", MagicMock(connect=mock_psycopg_connect)):
            import db  # noqa: F811

            db.connect(role="sales_manager", password="sales")
        call_kwargs = mock_psycopg_connect.call_args[1]
        assert call_kwargs["user"] == "sales_manager"
        assert call_kwargs["password"] == "sales"


class TestClose:
    """close() clears _CONN."""

    def test_close_calls_connection_close(self):
        """close() calls .close() on the underlying connection."""
        mock_conn = MagicMock()

        with patch("db.psycopg", MagicMock(connect=MagicMock(return_value=mock_conn))):
            import db  # noqa: F811

            db.connect()
            db.close()
        mock_conn.close.assert_called_once()

    def test_close_when_not_connected(self):
        """close() does not raise when _CONN is already None."""
        import db  # noqa: F811

        db._CONN = None
        db.close()  # should not raise


class TestGetConnAfterConnect:
    """get_conn() returns the stored connection after connect()."""

    def test_get_conn_returns_connection(self):
        """get_conn() returns the same connection object."""
        mock_conn = MagicMock()

        with patch("db.psycopg", MagicMock(connect=MagicMock(return_value=mock_conn))):
            import db  # noqa: F811

            db.connect()
            conn = db.get_conn()
        assert conn is mock_conn
