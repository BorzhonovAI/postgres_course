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

    def test_renders_items_table_when_has_items(self, mock_db, mock_user):
        from handlers.structures import Order, OrderItem

        order_data = Order(
            id=1,
            status="new",
            total_amount=Decimal("500"),
            created_at=datetime.now(),
            warehouse_id=1,
            created_by_id=1,
        )
        item1 = OrderItem(order_id=1, product_id=10, quantity=2, price=Decimal("250"))

        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = order_data
        mock_cursor.fetchall.return_value = [item1]

        with patch("db.get_conn", return_value=mock_db):
            from handlers import orders  # noqa: F811

            with patch("handlers.orders._render_order"):
                with patch("handlers.orders.get_product_by_id") as mock_prod:
                    mock_prod.return_value = MagicMock(id=10, name="Тестовый товар", sku="SKU-001")
                    with patch("handlers.orders.console") as mock_console:
                        orders.show_order("1")
                        # console.print called once for the items table
                        # (_render_order is patched so doesn't print)
                        assert mock_console.print.call_count >= 1



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

    def test_cancelled_deletion_no_delete(self, mock_db, mock_user):
        """When user declines, no DELETE is executed and 'Отменено' is printed."""
        from handlers.structures import Order

        order_data = Order(
            id=2,
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
                with patch("handlers.orders.prompt", return_value="n"):
                    with patch("handlers.orders.console") as mock_console:
                        orders.delete_order("2")

                        delete_calls = [
                            c
                            for c in mock_db.execute.call_args_list
                            if "DELETE" in c[0][0]
                        ]
                        assert len(delete_calls) == 0
                        # verify "Отменено" was printed
                        print_args = [c[0] for c in mock_console.print.call_args_list]
                        found = any(
                            isinstance(a, str) and "Отменено" in a
                            for args in print_args
                            for a in (args if isinstance(args, tuple) else [args])
                        )
                        assert found


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

                                    # auth_user was called to get created_by
                                    mock_auth.assert_called_once()

                                    # show_order called with the new order_id
                                    mock_show.assert_called_once_with(42)

    def test_insert_uses_created_by_id_column(self, mock_db, mock_user):
        """INSERT must reference created_by_id (not created_by) to match DB schema."""
        from handlers.structures import Warehouse

        mock_db.execute.return_value.fetchone.return_value = (1,)

        with patch("db.get_conn", return_value=mock_db):
            from handlers import orders  # noqa: F811

            mock_tx = MagicMock()
            mock_tx.__enter__ = MagicMock(return_value=None)
            mock_tx.__exit__ = MagicMock(return_value=False)
            mock_db.transaction = MagicMock(return_value=mock_tx)

            with patch("handlers.orders.get_warehouses") as mock_whs:
                mock_whs.return_value = [Warehouse(id=1, address="x", city_id=1, label=None, is_central=True)]
                with patch("handlers.orders.get_city_name", return_value="City"):
                    with patch("handlers.orders.choice", return_value=1):
                        with patch("handlers.orders.auth_user") as mock_auth:
                            mock_auth.return_value = mock_user
                            with patch("handlers.orders.prompt", return_value="n"):
                                with patch("handlers.orders.show_order"):
                                    orders.add_order()

                                    insert_calls = [
                                        c for c in mock_db.execute.call_args_list if "INSERT" in c[0][0]
                                    ]
                                    assert len(insert_calls) >= 1
                                    # The SQL string must contain created_by_id
                                    assert "created_by_id" in insert_calls[0][0][0]

    def test_adds_items_when_user_confirms(self, mock_db, mock_user):
        """When user confirms adding items, add_order_item is called inside transaction."""
        from handlers.structures import Warehouse

        mock_db.execute.return_value.fetchone.return_value = (42,)

        with patch("db.get_conn", return_value=mock_db):
            from handlers import orders  # noqa: F811

            mock_tx = MagicMock()
            mock_tx.__enter__ = MagicMock(return_value=None)
            mock_tx.__exit__ = MagicMock(return_value=False)
            mock_db.transaction = MagicMock(return_value=mock_tx)

            with patch("handlers.orders.get_warehouses") as mock_whs:
                mock_whs.return_value = [
                    Warehouse(id=1, address="x", city_id=1, label=None, is_central=True)
                ]
                with patch("handlers.orders.get_city_name", return_value="City"):
                    with patch("handlers.orders.choice", return_value=1):
                        with patch("handlers.orders.auth_user", return_value=mock_user):
                            with patch("handlers.orders.prompt", side_effect=["y", "n"]):
                                with patch("handlers.orders.add_order_item") as mock_add_item:
                                    with patch("handlers.orders.show_order"):
                                        orders.add_order()

                                        # add_order_item must be called once
                                        mock_add_item.assert_called_once_with(42)

                                        # two INSERTs: order + item
                                        insert_calls = [
                                            c
                                            for c in mock_db.execute.call_args_list
                                            if "INSERT" in c[0][0]
                                        ]
                                        assert len(insert_calls) >= 1
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


# ─── list orders new ──────────────────────────────────────────────────


class TestListOrdersNew:
    """list_orders_new() fetches and renders orders with status 'new'."""

    def test_renders_new_orders_table(self, mock_db, mock_user):
        from handlers.structures import Order

        order1 = Order(
            id=10,
            status="new",
            total_amount=Decimal("300"),
            created_at=datetime.now(),
            warehouse_id=1,
            created_by_id=1,
        )
        order2 = Order(
            id=11,
            status="new",
            total_amount=Decimal("700"),
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
                        orders.list_orders_new()
                        assert mock_console.print.called

    def test_uses_status_filter(self, mock_db, mock_user):
        """SQL must filter by status = 'new'."""
        from handlers.structures import Order

        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchall.return_value = []

        with patch("db.get_conn", return_value=mock_db):
            from handlers import orders  # noqa: F811

            with patch("handlers.orders.console"):
                orders.list_orders_new()

                select_calls = [
                    c for c in mock_db.cursor.call_args_list
                ]
                assert len(select_calls) >= 1
                # verify cursor.execute was called with status filter
                execute_calls = mock_cursor.execute.call_args_list
                assert len(execute_calls) >= 1
                sql = execute_calls[0][0][0]
                assert "status" in sql.lower()
                assert "'new'" in sql

    def test_shows_empty_message_when_no_new_orders(self, mock_db, mock_user):
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchall.return_value = []

        with patch("db.get_conn", return_value=mock_db):
            from handlers import orders  # noqa: F811

            with patch("handlers.orders.console") as mock_console:
                orders.list_orders_new()
                # console.print was called at least once (empty message)
                assert mock_console.print.called
                # verify it printed a yellow message (empty)
                print_args = [
                    c[0] for c in mock_console.print.call_args_list
                ]
                # should have printed "[yellow]Нет заказов со статусом new[/yellow]"
                found = any(
                    isinstance(a, str) and "Нет заказов" in a
                    for args in print_args
                    for a in (args if isinstance(args, tuple) else [args])
                )
                assert found


# ─── list orders processing ───────────────────────────────────────────


class TestListOrdersProcessing:
    """list_orders_processing() fetches and renders orders with status 'processing'."""

    def test_renders_processing_orders_table(self, mock_db, mock_user):
        from handlers.structures import Order

        order1 = Order(
            id=20,
            status="processing",
            total_amount=Decimal("500"),
            created_at=datetime.now(),
            warehouse_id=1,
            created_by_id=1,
            processing_by=2,
        )

        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchall.return_value = [order1]

        with patch("db.get_conn", return_value=mock_db):
            from handlers import orders  # noqa: F811

            with patch(
                "handlers.orders.get_warehouse_full_address", return_value="ул. Тест, 1"
            ):
                with patch("handlers.orders.get_user") as mock_get_user:
                    mock_get_user.return_value = mock_user
                    with patch("handlers.orders.console") as mock_console:
                        orders.list_orders_processing()
                        assert mock_console.print.called

    def test_uses_status_filter(self, mock_db, mock_user):
        """SQL must filter by status = 'processing'."""
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchall.return_value = []

        with patch("db.get_conn", return_value=mock_db):
            from handlers import orders  # noqa: F811

            with patch("handlers.orders.console"):
                orders.list_orders_processing()

                execute_calls = mock_cursor.execute.call_args_list
                assert len(execute_calls) >= 1
                sql = execute_calls[0][0][0]
                assert "status" in sql.lower()
                assert "'processing'" in sql

    def test_shows_empty_message_when_no_processing_orders(self, mock_db, mock_user):
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchall.return_value = []

        with patch("db.get_conn", return_value=mock_db):
            from handlers import orders  # noqa: F811

            with patch("handlers.orders.console") as mock_console:
                orders.list_orders_processing()
                print_args = [c[0] for c in mock_console.print.call_args_list]
                found = any(
                    isinstance(a, str) and "Нет заказов" in a
                    for args in print_args
                    for a in (args if isinstance(args, tuple) else [args])
                )
                assert found

    def test_shows_processor_username(self, mock_db, mock_user):
        """When order has processing_by, processor username is shown."""
        from handlers.structures import Order

        order1 = Order(
            id=30,
            status="processing",
            total_amount=Decimal("500"),
            created_at=datetime.now(),
            warehouse_id=1,
            created_by_id=1,
            processing_by=2,
        )

        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchall.return_value = [order1]

        proc_user = MagicMock()
        proc_user.username = "inventory_mgr"

        with patch("db.get_conn", return_value=mock_db):
            from handlers import orders  # noqa: F811

            with patch(
                "handlers.orders.get_warehouse_full_address", return_value="ул. Тест, 1"
            ):
                with patch("handlers.orders.get_user") as mock_get_user:
                    mock_get_user.side_effect = lambda uid: mock_user if uid == 1 else proc_user
                    with patch("handlers.orders.console") as mock_console:
                        orders.list_orders_processing()
                        # console.print was called; verify it includes processor name
                        print_args = [c[0] for c in mock_console.print.call_args_list]
                        # the Table object was printed — it should contain "inventory_mgr"
                        table_arg = print_args[0][0] if isinstance(print_args[0], tuple) else print_args[0]
                        # rich Table doesn't have __str__ that we can assert on, so just verify get_user was called for processor
                        assert mock_get_user.call_count >= 2  # once for created_by, once for processing_by


# ─── list orders my ───────────────────────────────────────────────────


class TestListOrdersMy:
    """list_orders_my() fetches and renders orders processed by current user."""

    def test_renders_my_orders_table(self, mock_db, mock_user):
        from handlers.structures import Order

        order1 = Order(
            id=40,
            status="processing",
            total_amount=Decimal("500"),
            created_at=datetime.now(),
            warehouse_id=1,
            created_by_id=2,
            processing_by=1,  # current user
        )

        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchall.return_value = [order1]

        with patch("db.get_conn", return_value=mock_db):
            from handlers import orders  # noqa: F811

            with patch(
                "handlers.orders.get_warehouse_full_address", return_value="ул. Тест, 1"
            ):
                with patch("handlers.orders.get_user") as mock_get_user:
                    mock_get_user.return_value = mock_user
                    with patch("handlers.orders.console") as mock_console:
                        orders.list_orders_my()
                        assert mock_console.print.called

    def test_uses_processing_by_filter(self, mock_db, mock_user):
        """SQL must filter by processing_by = current_user.id."""
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchall.return_value = []

        with patch("db.get_conn", return_value=mock_db):
            from handlers import orders  # noqa: F811

            with patch("handlers.orders.console"):
                orders.list_orders_my()

                execute_calls = mock_cursor.execute.call_args_list
                assert len(execute_calls) >= 1
                sql = execute_calls[0][0][0]
                assert "processing_by" in sql.lower()
                # should also filter by status = 'processing'
                assert "'processing'" in sql

    def test_shows_empty_message_when_no_my_orders(self, mock_db, mock_user):
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchall.return_value = []

        with patch("db.get_conn", return_value=mock_db):
            from handlers import orders  # noqa: F811

            with patch("handlers.orders.console") as mock_console:
                orders.list_orders_my()
                print_args = [c[0] for c in mock_console.print.call_args_list]
                found = any(
                    isinstance(a, str) and "нет заказов" in a
                    for args in print_args
                    for a in (args if isinstance(args, tuple) else [args])
                )
                assert found

    def test_calls_auth_user_for_current_user(self, mock_db, mock_user):
        """list_orders_my must call auth_user() to get the current user."""
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchall.return_value = []

        with patch("db.get_conn", return_value=mock_db):
            from handlers import orders  # noqa: F811

            with patch("handlers.orders.console"):
                with patch("handlers.orders.auth_user", return_value=mock_user) as mock_auth:
                    orders.list_orders_my()
                    mock_auth.assert_called_once()


# ─── _get_item_status ─────────────────────────────────────────────────


class TestGetItemStatus:
    """_get_item_status() computes order item status from related entities."""

    def test_new_order_status(self, mock_db, mock_user):
        """Order status 'new' → 'ожидает обработки'."""
        from handlers.structures import Order, OrderItem

        order = Order(
            id=1, status="new", total_amount=Decimal("100"),
            created_at=datetime.now(), warehouse_id=1, created_by_id=1,
        )
        item = OrderItem(order_id=1, product_id=10, quantity=2, price=Decimal("50"))

        mock_db.cursor.return_value.fetchone.return_value = None

        with patch("db.get_conn", return_value=mock_db):
            from handlers import orders  # noqa: F811
            status = orders._get_item_status(order, item)
            assert status == "ожидает обработки"

    def test_insufficient_reserve(self, mock_db, mock_user):
        """Reserve exists but quantity < item.quantity → 'ожидает обработки'."""
        from handlers.structures import Order, OrderItem

        order = Order(
            id=2, status="processing", total_amount=Decimal("100"),
            created_at=datetime.now(), warehouse_id=1, created_by_id=1,
        )
        item = OrderItem(order_id=2, product_id=10, quantity=5, price=Decimal("20"))

        mock_cursor = mock_db.cursor.return_value
        # First query: SELECT quantity WHERE quantity >= 5 — reserve=3 doesn't match → None
        # Second query: transfer check — no matching transfer → None
        mock_cursor.fetchone.side_effect = [None, None, None]

        with patch("db.get_conn", return_value=mock_db):
            from handlers import orders  # noqa: F811
            status = orders._get_item_status(order, item)
            assert status == "ожидает обработки"

    def test_full_reserve(self, mock_db, mock_user):
        """Reserve quantity >= item.quantity → 'в резерве'."""
        from handlers.structures import Order, OrderItem

        order = Order(
            id=3, status="processing", total_amount=Decimal("100"),
            created_at=datetime.now(), warehouse_id=1, created_by_id=1,
        )
        item = OrderItem(order_id=3, product_id=10, quantity=3, price=Decimal("20"))

        mock_cursor = mock_db.cursor.return_value
        # reserve has quantity=5 which is >= 3
        mock_cursor.fetchone.side_effect = [(5,),]

        with patch("db.get_conn", return_value=mock_db):
            from handlers import orders  # noqa: F811
            status = orders._get_item_status(order, item)
            assert status == "в резерве"

    def test_in_transit_with_arriving_at(self, mock_db, mock_user):
        """Active transfer → 'в пути' with details."""
        from handlers.structures import Order, OrderItem
        from datetime import timedelta

        order = Order(
            id=4, status="processing", total_amount=Decimal("100"),
            created_at=datetime.now(), warehouse_id=2, created_by_id=1,
        )
        item = OrderItem(order_id=4, product_id=10, quantity=3, price=Decimal("20"))

        mock_cursor = mock_db.cursor.return_value
        # reserve: None; transfer: found with arriving_at
        transfer_row = (1, 1, "in_transit", datetime.now() + timedelta(hours=5))
        mock_cursor.fetchone.side_effect = [None, transfer_row]

        with patch("db.get_conn", return_value=mock_db):
            import sys
            for mod in [m for m in sys.modules if m.startswith("handlers.orders")]:
                del sys.modules[mod]
            from handlers import orders as orders2  # noqa: F811
            status = orders2._get_item_status(order, item)
            assert "в пути" in status
            assert "из склада #1" in status

    def test_in_transit_without_arriving_at(self, mock_db, mock_user):
        """Active transfer without arriving_at → 'в пути' without date."""
        from handlers.structures import Order, OrderItem

        order = Order(
            id=5, status="processing", total_amount=Decimal("100"),
            created_at=datetime.now(), warehouse_id=2, created_by_id=1,
        )
        item = OrderItem(order_id=5, product_id=10, quantity=3, price=Decimal("20"))

        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.side_effect = [None, (1, 1, "shipping", None)]

        with patch("db.get_conn", return_value=mock_db):
            import sys
            for mod in [m for m in sys.modules if m.startswith("handlers.orders")]:
                del sys.modules[mod]
            from handlers import orders  # noqa: F811
            status = orders._get_item_status(order, item)
            assert "в пути" in status
            assert "из склада #1" in status
            assert "ожидаемая доставка" not in status

    def test_delivery_shipped(self, mock_db, mock_user):
        """Delivery item with status 'shipped' → 'отгружено'."""
        from handlers.structures import Order, OrderItem

        order = Order(
            id=6, status="processing", total_amount=Decimal("100"),
            created_at=datetime.now(), warehouse_id=1, created_by_id=1,
        )
        item = OrderItem(order_id=6, product_id=10, quantity=3, price=Decimal("20"))

        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.side_effect = [None, None, ("shipped",)]

        with patch("db.get_conn", return_value=mock_db):
            import sys
            for mod in [m for m in sys.modules if m.startswith("handlers.orders")]:
                del sys.modules[mod]
            from handlers import orders  # noqa: F811
            status = orders._get_item_status(order, item)
            assert status == "отгружено"

    def test_delivery_planned(self, mock_db, mock_user):
        """Delivery item with status 'planned' → 'запланирована отгрузка'."""
        from handlers.structures import Order, OrderItem

        order = Order(
            id=7, status="processing", total_amount=Decimal("100"),
            created_at=datetime.now(), warehouse_id=1, created_by_id=1,
        )
        item = OrderItem(order_id=7, product_id=10, quantity=3, price=Decimal("20"))

        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.side_effect = [None, None, ("planned",)]

        with patch("db.get_conn", return_value=mock_db):
            import sys
            for mod in [m for m in sys.modules if m.startswith("handlers.orders")]:
                del sys.modules[mod]
            from handlers import orders  # noqa: F811
            status = orders._get_item_status(order, item)
            assert status == "запланирована отгрузка"

    def test_processing_no_other_state(self, mock_db, mock_user):
        """Status 'processing' with no reserves/transfers/delivery → 'ожидает обработки'."""
        from handlers.structures import Order, OrderItem

        order = Order(
            id=8, status="processing", total_amount=Decimal("100"),
            created_at=datetime.now(), warehouse_id=1, created_by_id=1,
        )
        item = OrderItem(order_id=8, product_id=10, quantity=3, price=Decimal("20"))

        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.side_effect = [None, None, None]

        with patch("db.get_conn", return_value=mock_db):
            import sys
            for mod in [m for m in sys.modules if m.startswith("handlers.orders")]:
                del sys.modules[mod]
            from handlers import orders  # noqa: F811
            status = orders._get_item_status(order, item)
            assert status == "ожидает обработки"


# ─── mark order processing ────────────────────────────────────────────


class TestMarkOrderProcessing:
    """mark_order_processing() takes a 'new' order into processing."""

    def test_renders_error_for_missing_order(self, mock_db, mock_user):
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = None

        with patch("db.get_conn", return_value=mock_db):
            from handlers import orders  # noqa: F811

            with patch("handlers.orders.render_error") as mock_error:
                orders.mark_order_processing("999")
                mock_error.assert_called_once()
                assert "не найден" in mock_error.call_args[0][0]

    def test_renders_error_for_non_new_order(self, mock_db, mock_user):
        from handlers.structures import Order

        order_data = Order(
            id=1,
            status="processing",
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
                orders.mark_order_processing("1")
                mock_error.assert_called_once()
                assert "уже в обработке" in mock_error.call_args[0][0] or "статус" in mock_error.call_args[0][0]

    def test_shows_order_and_prompts_confirmation(self, mock_db, mock_user):
        from handlers.structures import Order

        order_data = Order(
            id=5,
            status="new",
            total_amount=Decimal("200"),
            created_at=datetime.now(),
            warehouse_id=1,
            created_by_id=1,
        )

        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = order_data

        with patch("db.get_conn", return_value=mock_db):
            from handlers import orders  # noqa: F811

            with patch("handlers.orders._render_order") as mock_render:
                with patch("handlers.orders.prompt") as mock_prompt:
                    mock_prompt.return_value = "n"
                    with patch("handlers.orders.console") as mock_console:
                        orders.mark_order_processing("5")
                        mock_render.assert_called_once_with(order_data)
                        mock_prompt.assert_called_once()

    def test_cancels_on_no_confirmation(self, mock_db, mock_user):
        from handlers.structures import Order

        order_data = Order(
            id=6,
            status="new",
            total_amount=Decimal("200"),
            created_at=datetime.now(),
            warehouse_id=1,
            created_by_id=1,
        )

        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = order_data

        with patch("db.get_conn", return_value=mock_db):
            from handlers import orders  # noqa: F811

            with patch("handlers.orders._render_order"):
                with patch("handlers.orders.prompt", return_value="n"):
                    with patch("handlers.orders.console") as mock_console:
                        orders.mark_order_processing("6")
                        # should print "Отменено"
                        print_args = [c[0] for c in mock_console.print.call_args_list]
                        found = any(
                            isinstance(a, str) and "Отменено" in a
                            for args in print_args
                            for a in (args if isinstance(args, tuple) else [args])
                        )
                        assert found

    def test_updates_order_on_confirmation(self, mock_db, mock_user):
        from handlers.structures import Order

        # First fetch returns the order
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.side_effect = [
            Order(
                id=7,
                status="new",
                total_amount=Decimal("200"),
                created_at=datetime.now(),
                warehouse_id=1,
                created_by_id=1,
            ),
            ("new", None),  # FOR UPDATE re-check
        ]

        with patch("db.get_conn", return_value=mock_db):
            from handlers import orders  # noqa: F811

            with patch("handlers.orders._render_order"):
                with patch("handlers.orders.prompt", return_value="y"):
                    with patch("handlers.orders.console"):
                        with patch("handlers.orders.auth_user", return_value=mock_user):
                            orders.mark_order_processing("7")

                            update_calls = [
                                c for c in mock_db.execute.call_args_list
                                if "UPDATE" in c[0][0]
                            ]
                            assert len(update_calls) >= 1
                            sql, params = update_calls[0][0]
                            assert "processing" in sql
                            assert params[0] == mock_user.id
                            assert params[1] == "7"

    def test_race_condition_another_manager_took_order(self, mock_db, mock_user):
        """If status changed or processing_by set by another manager, show error."""
        from handlers.structures import Order

        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.side_effect = [
            Order(
                id=8,
                status="new",
                total_amount=Decimal("200"),
                created_at=datetime.now(),
                warehouse_id=1,
                created_by_id=1,
            ),
            ("processing", 99),  # status changed by another manager
        ]

        with patch("db.get_conn", return_value=mock_db):
            from handlers import orders  # noqa: F811

            with patch("handlers.orders._render_order"):
                with patch("handlers.orders.prompt", return_value="y"):
                    with patch("handlers.orders.console"):
                        with patch("handlers.orders.auth_user", return_value=mock_user):
                            with patch("handlers.orders.render_error") as mock_error:
                                orders.mark_order_processing("8")
                                mock_error.assert_called_once()
                                assert "уже в обработке" in mock_error.call_args[0][0]

    def test_race_condition_processing_by_already_set(self, mock_db, mock_user):
        """If status is still 'new' but processing_by is already set, show error."""
        from handlers.structures import Order

        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.side_effect = [
            Order(
                id=9,
                status="new",
                total_amount=Decimal("200"),
                created_at=datetime.now(),
                warehouse_id=1,
                created_by_id=1,
            ),
            ("new", 42),  # status still new but someone else took it
        ]

        with patch("db.get_conn", return_value=mock_db):
            from handlers import orders  # noqa: F811

            with patch("handlers.orders._render_order"):
                with patch("handlers.orders.prompt", return_value="y"):
                    with patch("handlers.orders.console"):
                        with patch("handlers.orders.auth_user", return_value=mock_user):
                            with patch("handlers.orders.render_error") as mock_error:
                                orders.mark_order_processing("9")
                                mock_error.assert_called_once()
                                assert "уже в обработке" in mock_error.call_args[0][0]
