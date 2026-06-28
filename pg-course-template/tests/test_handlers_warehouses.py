"""Unit tests for warehouse handlers (handlers/warehouses.py).

Covers helper functions (warehouses_empty, warehouses_count, get_warehouse_by_id,
get_city_name) and commands (list_warehouses, show_warehouse).
Mutation commands (add, edit, delete) require interactive prompt mocking and
are tested separately.
"""

from unittest.mock import MagicMock, patch

import pytest


class TestWarehousesCount:
    """warehouses_count() returns the row count from catalog.warehouses."""

    def test_returns_integer_count(self, mock_db, mock_user):
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = (5,)

        with patch("db.get_conn", return_value=mock_db):
            from handlers import warehouses  # noqa: F811

            count = warehouses.warehouses_count()
            assert count == 5


class TestWarehousesEmpty:
    """warehouses_empty() delegates to warehouses_count()."""

    def test_true_when_no_warehouses(self, mock_db, mock_user):
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = (0,)

        with patch("db.get_conn", return_value=mock_db):
            from handlers import warehouses  # noqa: F811

            assert warehouses.warehouses_empty() is True

    def test_false_when_warehouses_exist(self, mock_db, mock_user):
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = (3,)

        with patch("db.get_conn", return_value=mock_db):
            from handlers import warehouses  # noqa: F811

            assert warehouses.warehouses_empty() is False


class TestGetWarehouseById:
    """get_warehouse_by_id() maps a row to a Warehouse dataclass."""

    def test_finds_existing_warehouse(self, mock_db, mock_user):
        from handlers.structures import Warehouse

        warehouse_data = Warehouse(
            id=1, city_id=2, address="ул. Ленина 10", label="Главный", is_central=True
        )

        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = warehouse_data

        with patch("db.get_conn", return_value=mock_db):
            from handlers import warehouses  # noqa: F811

            result = warehouses.get_warehouse_by_id(1)
            assert result is not None
            assert result.id == 1
            assert result.address == "ул. Ленина 10"
            assert result.is_central is True

    def test_returns_none_for_unknown_id(self, mock_db, mock_user):
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = None

        with patch("db.get_conn", return_value=mock_db):
            from handlers import warehouses  # noqa: F811

            result = warehouses.get_warehouse_by_id(999)
            assert result is None


class TestGetCityName:
    """get_city_name() looks up a city name by ID."""

    def test_returns_city_name(self, mock_db, mock_user):
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = "Москва"

        with patch("db.get_conn", return_value=mock_db):
            from handlers import warehouses  # noqa: F811

            name = warehouses.get_city_name(1)
            assert name == "Москва"


class TestListWarehouses:
    """list_warehouses() renders a table of all warehouses."""

    def test_prints_table(self, mock_db, mock_user):
        from handlers.structures import Warehouse

        wh1 = Warehouse(id=1, city_id=1, address="ул. А 1", label="A", is_central=True)
        wh2 = Warehouse(
            id=2, city_id=2, address="ул. Б 2", label=None, is_central=False
        )

        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchall.return_value = [wh1, wh2]
        # get_city_name is called per-warehouse inside list_warehouses;
        # each call gets a fresh cursor from mock_db.cursor(), but since
        # mock_db.cursor returns the same mock_cursor, we need to handle
        # the method chain. The helper calls conn.cursor() again, so we
        # mock get_city_name to avoid cursor conflict.

        with patch("db.get_conn", return_value=mock_db):
            from handlers import warehouses  # noqa: F811

            with patch.object(warehouses, "get_city_name", return_value="Город"):
                with patch("handlers.warehouses.console") as mock_console:
                    warehouses.list_warehouses()
                    assert mock_console.print.call_count >= 1


class TestShowWarehouse:
    """show_warehouse() renders a single warehouse or shows an error."""

    def test_shows_existing_warehouse(self, mock_db, mock_user):
        from handlers.structures import Warehouse

        wh = Warehouse(id=3, city_id=1, address="ул. В 5", label="В", is_central=False)

        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = wh

        with patch("db.get_conn", return_value=mock_db):
            from handlers import warehouses  # noqa: F811

            with patch("handlers.warehouses.console") as mock_console:
                with patch.object(warehouses, "get_city_name", return_value="Город"):
                    warehouses.show_warehouse("3")
                    assert mock_console.print.call_count >= 1

    def test_renders_error_for_missing_warehouse(self, mock_db, mock_user):
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = None

        with patch("db.get_conn", return_value=mock_db):
            from handlers import warehouses  # noqa: F811

            with patch("handlers.warehouses.render_error") as mock_error:
                warehouses.show_warehouse("999")
                mock_error.assert_called_once()
                assert "не найден" in mock_error.call_args[0][0]


class TestGetWarehouses:
    """get_warehouses() returns a list of all Warehouse objects."""

    def test_returns_list_of_warehouses(self, mock_db, mock_user):
        from handlers.structures import Warehouse

        wh1 = Warehouse(id=1, city_id=1, address="ул. 1", label=None, is_central=True)
        wh2 = Warehouse(id=2, city_id=2, address="ул. 2", label="B", is_central=False)

        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchall.return_value = [wh1, wh2]

        with patch("db.get_conn", return_value=mock_db):
            from handlers import warehouses  # noqa: F811

            result = warehouses.get_warehouses()
            assert len(result) == 2
            assert result[0].id == 1
            assert result[1].label == "B"
