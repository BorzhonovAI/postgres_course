"""Sanity check — ensures the test harness boots and global-state reset works."""


def test_global_state_reset():
    """After autouse fixture, singletons should be clean."""
    import auth
    import commands
    import db

    assert db._CONN is None
    assert auth._USER is None
    assert commands._COMMANDS_REGISTRY == []


def test_mock_db_fixture(mock_db):  # noqa: F811
    """mock_db fixture injects a usable mock connection."""
    import db
    conn = db.get_conn()
    assert conn is not None
