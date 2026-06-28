"""Unit tests for order handlers (handlers/orders.py).

Covers helper functions (_render_order) and commands (list, show, add, edit,
delete, publish orders). Tests published-order protection, status transitions,
and error paths.
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest


class TestShowOrder:
    """show_order() renders an existing order or shows an error."""

    def test_renders_error_for_missing_order(self, mock_db, mock_user):
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = None

        with patch("db.get_conn", return_value=mock_db):
            from handlers import orders  # noqa: F811

            with patch("handlers.orders.render_error") as mock_error:
                orders.show_order("999")
                mock_error.assert_called_once()
                assert "не найден" in mock_error.call_args[0][0]

    def test_renders_existing_order(self, mock_db, mock_user):
        from handlers.structures import Order

        order_data = Order(
            id=1,
            status="unpublished",
            total_amount=Decimal("500"),
            created_at=datetime.now(),
            warehouse_id=1,
            created_by_id=1,
        )

        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = order_data

        with patch("db.get_conn", return_value=mock_db):
            from handlers import orders  # noqa: F811

            with patch("handlers.orders._render_order") as mock_render:
                orders.show_order("1")
                mock_render.assert_called_once_with(order_data)


class TestEditOrder:
    """edit_order() modifies an unpublished order or shows an error."""

    def test_renders_error_for_missing_order(self, mock_db, mock_user):
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = None

        with patch("db.get_conn", return_value=mock_db):
            from handlers import orders  # noqa: F811

            with patch("handlers.orders.render_error") as mock_error:
                orders.edit_order("999")
                mock_error.assert_called_once()
                assert "не найден" in mock_error.call_args[0][0]

    def test_renders_error_for_published_order(self, mock_db, mock_user):
        from handlers.structures import Order

        order_data = Order(
            id=1,
            status="new",
            total_amount=Decimal("500"),
            created_at=datetime.now(),
            warehouse_id=1,
            created_by_id=1,
        )

        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = order_data

        with patch("db.get_conn", return_value=mock_db):
            from handlers import orders  # noqa: F811

            with patch("handlers.orders.render_error") as mock_error:
                orders.edit_order("1")
                mock_error.assert_called_once()
                assert "опубликован" in mock_error.call_args[0][0]

    def test_edits_unpublished_order(self, mock_db, mock_user):
        from handlers.structures import Order, Warehouse

        order_data = Order(
            id=1,
            status="unpublished",
            total_amount=Decimal("100"),
            created_at=datetime.now(),
            warehouse_id=1,
            created_by_id=1,
        )

        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = order_data

        with patch("db.get_conn", return_value=mock_db):
            from handlers import orders  # noqa: F811

            with patch("handlers.orders.get_warehouses") as mock_whs:
                mock_whs.return_value = [
                    Warehouse(
                        id=1,
                        address="ул. Тест, 1",
                        city_id=1,
                        label="test",
                        is_central=True,
                    )
                ]
                with patch("handlers.orders.get_city_name", return_value="Город"):
                    with patch("handlers.orders.choice", return_value=1):
                        with patch("handlers.orders.console") as mock_console:
                            orders.edit_order("1")

                            # UPDATE executed
                            update_calls = [
                                c
                                for c in mock_db.execute.call_args_list
                                if "UPDATE" in c[0][0]
                            ]
                            assert len(update_calls) >= 1
                            assert mock_console.print.called


class TestDeleteOrder:
    """delete_order() removes an unpublished order or shows an error."""

    def test_renders_error_for_missing_order(self, mock_db, mock_user):
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = None

        with patch("db.get_conn", return_value=mock_db):
            from handlers import orders  # noqa: F811

            with patch("handlers.orders.render_error") as mock_error:
                orders.delete_order("999")
                mock_error.assert_called_once()
                assert "не найден" in mock_error.call_args[0][0]

    def test_renders_error_for_published_order(self, mock_db, mock_user):
        from handlers.structures import Order

        order_data = Order(
            id=1,
            status="new",
            total_amount=Decimal("500"),
            created_at=datetime.now(),
            warehouse_id=1,
            created_by_id=1,
        )

        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = order_data

        with patch("db.get_conn", return_value=mock_db):
            from handlers import orders  # noqa: F811

            with patch("handlers.orders.render_error") as mock_error:
                orders.delete_order("1")
                mock_error.assert_called_once()
                assert "опубликован" in mock_error.call_args[0][0]

    def test_deletes_unpublished_order_on_confirmation(self, mock_db, mock_user):
        from handlers.structures import Order

        order_data = Order(
            id=1,
            status="unpublished",
            total_amount=Decimal("100"),
            created_at=datetime.now(),
            warehouse_id=1,
            created_by_id=1,
        )

        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = order_data

        with patch("db.get_conn", return_value=mock_db):
            from handlers import orders  # noqa: F811

            with patch("handlers.orders._render_order"):
                with patch("handlers.orders.prompt", return_value="y"):
                    with patch("handlers.orders.console") as mock_console:
                        orders.delete_order("1")

                        delete_calls = [
                            c
                            for c in mock_db.execute.call_args_list
                            if "DELETE" in c[0][0]
                        ]
                        assert len(delete_calls) >= 1
                        assert mock_console.print.called


class TestPublishOrder:
    """publish_order() changes status from unpublished to new."""

    def test_renders_error_for_missing_order(self, mock_db, mock_user):
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = None

        with patch("db.get_conn", return_value=mock_db):
            from handlers import orders  # noqa: F811

            with patch("handlers.orders.render_error") as mock_error:
                orders.publish_order("999")
                mock_error.assert_called_once()
                assert "не найден" in mock_error.call_args[0][0]

    def test_renders_error_for_already_published_order(self, mock_db, mock_user):
        from handlers.structures import Order

        order_data = Order(
            id=1,
            status="new",
            total_amount=Decimal("500"),
            created_at=datetime.now(),
            warehouse_id=1,
            created_by_id=1,
        )

        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = order_data

        with patch("db.get_conn", return_value=mock_db):
            from handlers import orders  # noqa: F811

            with patch("handlers.orders.render_error") as mock_error:
                orders.publish_order("1")
                mock_error.assert_called_once()
                assert "уже опубликован" in mock_error.call_args[0][0]

    def test_changes_status_to_new(self, mock_db, mock_user):
        from handlers.structures import Order

        order_data = Order(
            id=1,
            status="unpublished",
            total_amount=Decimal("100"),
            created_at=datetime.now(),
            warehouse_id=1,
            created_by_id=1,
        )

        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = order_data

        with patch("db.get_conn", return_value=mock_db):
            from handlers import orders  # noqa: F811

            with patch("handlers.orders.console") as mock_console:
                orders.publish_order("1")

                update_calls = [
                    c for c in mock_db.execute.call_args_list if "UPDATE" in c[0][0]
                ]
                assert len(update_calls) >= 1

                # Verify status parameter is "new"
                update_params = update_calls[0][0][1]  # (sql, params) → params
                assert update_params[0] == "new"
                assert mock_console.print.called


class TestAddOrder:
    """add_order() creates an order in a transaction with auth_user binding."""

    def test_creates_order_in_transaction(self, mock_db, mock_user):
        from handlers.structures import Warehouse, Order

        # conn.execute("INSERT ... RETURNING id").fetchone() returns the new id
        mock_db.execute.return_value.fetchone.return_value = (42,)

        with patch("db.get_conn", return_value=mock_db):
            from handlers import orders  # noqa: F811

            # Mock transaction context manager
            mock_tx = MagicMock()
            mock_tx.__enter__ = MagicMock(return_value=None)
            mock_tx.__exit__ = MagicMock(return_value=False)
            mock_db.transaction = MagicMock(return_value=mock_tx)

            with patch("handlers.orders.get_warehouses") as mock_whs:
                mock_whs.return_value = [
                    Warehouse(
                        id=1,
                        address="ул. Тест, 1",
                        city_id=1,
                        label="test",
                        is_central=True,
                    )
                ]
                with patch("handlers.orders.get_city_name", return_value="Город"):
                    with patch("handlers.orders.choice", return_value=1):
                        with patch("handlers.orders.auth_user") as mock_auth:
                            mock_auth.return_value = mock_user
                            with patch("handlers.orders.prompt", return_value="n"):
                                with patch("handlers.orders.show_order") as mock_show:
                                    orders.add_order()

                                    # INSERT executed via conn.execute
                                    insert_calls = [
                                        c
                                        for c in mock_db.execute.call_args_list
                                        if "INSERT" in c[0][0]
                                    ]
                                    assert len(insert_calls) >= 1

                                    # auth_user was called to get created_by_id
                                    mock_auth.assert_called_once()

                                    # show_order called with the new order_id
                                    mock_show.assert_called_once_with(42)


class TestListOrders:
    """list_orders() fetches and renders all orders."""

    def test_renders_orders_table(self, mock_db, mock_user):
        from handlers.structures import Order

        order1 = Order(
            id=1,
            status="unpublished",
            total_amount=Decimal("100"),
            created_at=datetime.now(),
            warehouse_id=1,
            created_by_id=1,
        )
        order2 = Order(
            id=2,
            status="new",
            total_amount=Decimal("500"),
            created_at=datetime.now(),
            warehouse_id=2,
            created_by_id=1,
        )

        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchall.return_value = [order1, order2]

        with patch("db.get_conn", return_value=mock_db):
            from handlers import orders  # noqa: F811

            with patch(
                "handlers.orders.get_warehouse_full_address", return_value="ул. Тест, 1"
            ):
                with patch("handlers.orders.get_user") as mock_get_user:
                    mock_get_user.return_value = mock_user
                    with patch("handlers.orders.console") as mock_console:
                        orders.list_orders()
                        assert mock_console.print.called

    def test_renders_empty_table_when_no_orders(self, mock_db, mock_user):
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchall.return_value = []

        with patch("db.get_conn", return_value=mock_db):
            from handlers import orders  # noqa: F811

            with patch("handlers.orders.console") as mock_console:
                orders.list_orders()
                assert mock_console.print.called
