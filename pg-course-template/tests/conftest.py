"""Shared fixtures and configuration for the test suite."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# ─── Environment defaults ──────────────────────────────────────────────
# db.py reads env vars at module-level. Set safe defaults so importing
# the module doesn't raise KeyError during tests.  Real integration
# tests will override these explicitly.

for _key, _default in [
    ("DB_NAME", "inventorydb"),
    ("DB_USER", "app_user"),
    ("DB_PASSWORD", "gfhjkm"),
    ("DB_HOST", "localhost"),
    ("DB_PORT", "5432"),
]:
    os.environ.setdefault(_key, _default)

# ─── Global state reset ───────────────────────────────────────────────
# db.py, auth.py, and commands.py hold module-level mutable singletons.
# Reset them before every test so tests don't leak state into each other.


@pytest.fixture(autouse=True)
def _reset_global_state():
    """Reset _CONN, _USER, and _COMMANDS_REGISTRY before each test."""
    # Reset db._CONN
    import db  # noqa: F811

    db._CONN = None

    # Reset auth._USER
    import auth  # noqa: F811

    auth._USER = None

    # Reset commands registry
    import commands  # noqa: F811

    commands._COMMANDS_REGISTRY.clear()

    # Force handlers to re-register on next import by removing them
    # from sys.modules so @command decorators run again.
    _handler_modules = [name for name in sys.modules if name.startswith("handlers.")]
    for mod in _handler_modules:
        del sys.modules[mod]
    # Also remove the handlers __init__ so auto-dispatch re-imports modules
    if "handlers" in sys.modules:
        del sys.modules["handlers"]


# ─── Mock DB connection ──────────────────────────────────────────────
# Provides a fake psycopg.Connection for unit tests that don't need
# a real database.  Tests requesting this fixture get `db.get_conn()`
# returning the mock; they MUST NOT import handlers (which would auto-
# register commands and reach for the real connection).


@pytest.fixture
def mock_db():
    """Return a mock psycopg.Connection injected via db._CONN."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    # cursor context manager returns self
    mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
    mock_cursor.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor = MagicMock(return_value=mock_cursor)

    import db  # noqa: F811

    db._CONN = mock_conn

    try:
        yield mock_conn
    finally:
        db._CONN = None


# ─── Mock auth user ──────────────────────────────────────────────────


@pytest.fixture
def mock_user():
    """Create a fake authenticated User and set auth._USER."""
    from users import User  # noqa: F811

    user = User(id=1, username="test_user", role="catalog_manager")

    import auth  # noqa: F811

    auth._USER = user

    return user


# ─── Helpers ─────────────────────────────────────────────────────────


@pytest.fixture
def document():
    """Factory for prompt_toolkit Document objects used by validators."""
    from prompt_toolkit.document import Document

    def _make(text: str) -> Document:
        return Document(text)

    return _make
