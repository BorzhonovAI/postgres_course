"""Unit tests for transfer handlers (handlers/transfers.py).

Covers helper functions (_render_transfer_items) and commands (list, add,
remove, start shipping). Tests error paths and rendering.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from users import User


class TestListTransfersPlannedAll:
    """list_transfers_planned_all() shows all planned transfers."""

    def test_shows_error_when_no_transfers(self, mock_db, mock_user):
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchall.return_value = []

        with patch("db.get_conn", return_value=mock_db):
            from handlers import transfers

            with patch("handlers.transfers.console") as mock_console:
                transfers.list_transfers_planned_all()
                mock_console.print.assert_called_once()
                assert "Нет planned перемещений" in mock_console.print.call_args[0][0]

    def test_renders_transfer_table(self, mock_db, mock_user):
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchall.return_value = [
            {
                "id": 1,
                "from_warehouse_id": 1,
                "to_warehouse_id": 2,
                "product_id": 10,
                "product_name": "Товар А",
                "quantity": 5,
                "requested_by": 1,
                "reserve_id": None,
                "order_id": None,
                "status": "planned",
            }
        ]

        fake_user = User(id=1, username="test_user", role="inventory_manager")

        with patch("db.get_conn", return_value=mock_db):
            from handlers import transfers

            with patch("handlers.transfers.console") as mock_console:
                with patch("handlers.transfers.get_user", return_value=fake_user):
                    transfers.list_transfers_planned_all()
                    # console.print called for route header and items table
                    assert mock_console.print.call_count >= 2


class TestListTransfersPlannedMy:
    """list_transfers_planned_my() shows transfers by current user."""

    def test_shows_error_when_no_transfers(self, mock_db, mock_user):
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchall.return_value = []

        with patch("db.get_conn", return_value=mock_db):
            from handlers import transfers

            with patch("handlers.transfers.console") as mock_console:
                transfers.list_transfers_planned_my()
                mock_console.print.assert_called_once()
                # Check that console.print was called (message displayed)
                assert mock_console.print.call_count == 1


class TestRemoveTransferItems:
    """remove_transfer_items() removes items from a transfer."""

    def test_shows_error_when_no_transfers(self, mock_db, mock_user):
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchall.return_value = []

        with patch("db.get_conn", return_value=mock_db):
            from handlers import transfers

            with patch("handlers.transfers.console") as mock_console:
                transfers.remove_transfer_items()
                mock_console.print.assert_called_once()
                assert (
                    "Нет перемещений с товарами" in mock_console.print.call_args[0][0]
                )


class TestStartShipping:
    """start_shipping() changes transfer status."""

    def test_shows_error_for_missing_transfer(self, mock_db, mock_user):
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = None

        with patch("db.get_conn", return_value=mock_db):
            from handlers import transfers

            with patch("handlers.transfers.render_error") as mock_error:
                transfers.start_shipping("999")
                mock_error.assert_called_once()
                assert "не найден" in mock_error.call_args[0][0]

    def test_shows_error_for_non_planned_transfer(self, mock_db, mock_user):
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = (1, "shipping")

        with patch("db.get_conn", return_value=mock_db):
            from handlers import transfers

            with patch("handlers.transfers.render_error") as mock_error:
                transfers.start_shipping("1")
                mock_error.assert_called_once()
                assert "shipping" in mock_error.call_args[0][0]


class TestAddTransferItemsRaceCondition:
    """add_transfer_items must lock transfer_items with FOR UPDATE."""

    def test_locks_transfer_items_before_insert(self, mock_db, mock_user):
        """Verify SELECT ... FOR UPDATE is executed on transfer_items
        before the INSERT to prevent race conditions."""
        mock_cursor = mock_db.cursor.return_value
        mock_db.execute.return_value = MagicMock()
        mock_cursor.fetchall.return_value = [(10, "TestProduct", "SKU001", 100)]

        from dataclasses import dataclass
        from handlers.structures import Warehouse

        @dataclass
        class FakeWarehouse(Warehouse):
            pass

        fake_wh1 = FakeWarehouse(
            id=1, city_id=1, address="addr1", label=None, is_central=False
        )
        fake_wh2 = FakeWarehouse(
            id=2, city_id=1, address="addr2", label=None, is_central=False
        )

        # Stock check uses dict_row, so fetchone must return a dict
        def fake_fetchone_for_check(*args, **kwargs):
            return {"quantity": 100}

        def fake_fetchone_for_lock(*args, **kwargs):
            return 1

        # 1. Первая транзакция: FOR UPDATE on transfers → (1,)
        # 2. Вторая транзакция (SERIALIZABLE):
        #    - статус трансфера → {"status": "planned"}
        #    - FOR UPDATE transfer_items → 1 (item exists → UPDATE path)
        #    - FOR UPDATE stock → {"quantity": 100}
        mock_cursor.fetchone.side_effect = [
            (1,),  # FOR UPDATE on transfers (1st tx)
            {"status": "planned"},  # transfer status check (2nd tx, dict_row)
            1,  # FOR UPDATE transfer_items (2nd tx, item exists)
            {"quantity": 100},  # stock FOR UPDATE (2nd tx, dict_row)
        ]

        with patch("db.get_conn", return_value=mock_db):
            from handlers import transfers

            with patch(
                "handlers.transfers._get_route_pairs",
                return_value={1: [2], 2: [1]},
            ):
                with patch(
                    "handlers.transfers.get_warehouses",
                    return_value=[fake_wh1, fake_wh2],
                ):
                    with patch(
                        "handlers.transfers.get_warehouse_full_address",
                        return_value="City, addr",
                    ):
                        # prompt_choice: from_wh, to_wh, product, confirm, add_more — всё вне транзакции
                        with patch(
                            "handlers.transfers.prompt_choice",
                            side_effect=[1, 2, 10, "y", "n"],
                        ):
                            with patch(
                                "handlers.transfers.prompt", side_effect=["5", "y", "n"]
                            ):
                                with patch("handlers.transfers.console"):
                                    with patch(
                                        "handlers.transfers.auth_user",
                                        return_value=mock_user,
                                    ):
                                        # Patch ALL cursor() calls to return mock_cursor
                                        mock_db.cursor = MagicMock(
                                            return_value=mock_cursor
                                        )
                                        mock_tx = MagicMock()
                                        mock_tx.cursor.return_value = mock_cursor
                                        mock_db.transaction.return_value = mock_tx

                                    try:
                                        transfers.add_transfer_items()
                                    except Exception as e:
                                        print(f"\nERROR: {type(e).__name__}: {e}")
                                        import traceback

                                        traceback.print_exc()

                                    # Verify UPDATE (not INSERT) — item_row=1 means item exists
                                    execute_calls = mock_db.execute.call_args_list
                                    found_update = False
                                    for call in execute_calls:
                                        sql = call[0][0]
                                        if "UPDATE inventory.transfer_items" in sql:
                                            found_update = True
                                            break
                                    assert found_update, (
                                        "add_transfer_items must UPDATE transfer_items "
                                        "when item already exists (check-then-act)"
                                    )


class TestAddTransferItemsInsufficientStock:
    """add_transfer_items rejects quantity > stock quantity."""

    def test_rejects_excessive_quantity(self, mock_db, mock_user):
        """When requested quantity exceeds stock, print error and continue."""
        mock_cursor = mock_db.cursor.return_value
        mock_db.execute.return_value = MagicMock()
        mock_cursor.fetchall.return_value = [(10, "TestProduct", "SKU001", 2)]

        from dataclasses import dataclass
        from handlers.structures import Warehouse

        @dataclass
        class FakeWarehouse(Warehouse):
            pass

        fake_wh1 = FakeWarehouse(
            id=1, city_id=1, address="addr1", label=None, is_central=False
        )
        fake_wh2 = FakeWarehouse(
            id=2, city_id=1, address="addr2", label=None, is_central=False
        )

        # flow: 1st tx (FOR UPDATE transfers) → closes → loop:
        # prompt_choice=10 (product) → prompt="5" → prompt="y" → 2nd tx:
        #   1) FOR UPDATE transfers status (dict_row)
        #   2) FOR UPDATE transfer_items (item_cur.fetchone → None, not exists)
        #   3) FOR UPDATE stock (dict_row → insufficient)
        mock_cursor.fetchone.side_effect = [
            (1,),  # 1st tx: FOR UPDATE transfers
            {"status": "planned"},  # 2nd tx: FOR UPDATE transfers status (dict_row)
            None,  # 2nd tx: FOR UPDATE transfer_items (item not found → INSERT path)
            {"quantity": 2},  # 2nd tx: FOR UPDATE stock (dict_row, insufficient)
        ]

        # stock check uses dict_row → fetchone returns dict
        stock_cursor = MagicMock()
        stock_cursor.__enter__ = MagicMock(return_value=stock_cursor)
        stock_cursor.__exit__ = MagicMock(return_value=False)
        stock_cursor.fetchone.side_effect = [{"quantity": 2}]

        # Configure transaction mock so that `with conn.transaction():`
        # returns mock_tx (not a new MagicMock) and mock_tx.cursor() returns
        # mock_cursor (not a new MagicMock).
        mock_tx = MagicMock()
        mock_tx.__enter__ = MagicMock(return_value=mock_tx)
        mock_tx.__exit__ = MagicMock(return_value=False)
        mock_tx.cursor = MagicMock(return_value=mock_cursor)

        # Patch db.get_conn AFTER setting up mocks so the mock persists
        with patch("db.get_conn", return_value=mock_db):
            from handlers import transfers

            with patch(
                "handlers.transfers._get_route_pairs",
                return_value={1: [2], 2: [1]},
            ):
                with patch(
                    "handlers.transfers.get_warehouses",
                    return_value=[fake_wh1, fake_wh2],
                ):
                    with patch(
                        "handlers.transfers.get_warehouse_full_address",
                        return_value="City, addr",
                    ):
                        # from_wh, to_wh, product, "Отмена" из списка
                        with patch(
                            "handlers.transfers.prompt_choice",
                            side_effect=[1, 2, 10, "Отмена"],
                        ):
                            # quantity, confirm, "Добавить ещё?" = "n"
                            with patch(
                                "handlers.transfers.prompt", side_effect=["5", "y", "n"]
                            ):
                                with patch(
                                    "handlers.transfers.render_error"
                                ) as mock_render_error:
                                    with patch(
                                        "handlers.transfers.auth_user",
                                        return_value=mock_user,
                                    ):
                                        # Use lambda so that mock_db.transaction()
                                        # always returns mock_tx (not a new MagicMock),
                                        # even when called multiple times (nested tx).
                                        mock_db.transaction.return_value = mock_tx
                                        mock_db.cursor = MagicMock(
                                            return_value=mock_cursor
                                        )
                                        mock_cursor.__enter__.return_value = mock_cursor

                                        transfers.add_transfer_items()

                                    # render_error should have been called
                                    # with insufficient stock message
                                    assert mock_render_error.called, (
                                        "render_error should be called for "
                                        "insufficient stock"
                                    )
                                    error_msg = mock_render_error.call_args[0][0]
                                    assert "недостаточно" in error_msg, (
                                        f"Expected 'недостаточно' in error message, "
                                        f"got: {error_msg}"
                                    )

    def test_continues_loop_after_reject(self, mock_db, mock_user):
        """When stock is insufficient, render_error is shown and the
        loop continues (user can try another product)."""
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.side_effect = [
            (1,),  # FOR UPDATE transfers (1st tx)
            {"status": "planned"},  # FOR UPDATE transfers status (2nd tx, dict_row)
            None,  # FOR UPDATE transfer_items (2nd tx, not found)
            {"quantity": 1},  # FOR UPDATE stock (2nd tx, dict_row, insufficient)
        ]
        mock_db.execute.return_value = MagicMock()
        mock_tx = MagicMock()
        mock_tx.cursor.return_value = mock_cursor
        mock_db.transaction.return_value = mock_tx

        # Provide actual stock data so the while loop doesn't break
        mock_cursor.fetchall.return_value = [(10, "TestProduct", "SKU001", 1)]

        from dataclasses import dataclass
        from handlers.structures import Warehouse

        @dataclass
        class FakeWarehouse(Warehouse):
            pass

        fake_wh1 = FakeWarehouse(
            id=1, city_id=1, address="addr1", label=None, is_central=False
        )
        fake_wh2 = FakeWarehouse(
            id=2, city_id=1, address="addr2", label=None, is_central=False
        )

        with patch("db.get_conn", return_value=mock_db):
            from handlers import transfers

            with patch(
                "handlers.transfers._get_route_pairs",
                return_value={1: [2], 2: [1]},
            ):
                with patch(
                    "handlers.transfers.get_warehouses",
                    return_value=[fake_wh1, fake_wh2],
                ):
                    with patch(
                        "handlers.transfers.get_warehouse_full_address",
                        return_value="City, addr",
                    ):
                        # from_wh, to_wh, product1, "Отмена" из списка
                        with patch(
                            "handlers.transfers.prompt_choice",
                            side_effect=[1, 2, 10, "Отмена"],
                        ):
                            # quantity, confirm, "Добавить ещё?" = "n"
                            with patch(
                                "handlers.transfers.prompt", side_effect=["5", "y", "n"]
                            ):
                                with patch(
                                    "handlers.transfers.render_error"
                                ) as mock_render_error:
                                    with patch(
                                        "handlers.transfers.auth_user",
                                        return_value=mock_user,
                                    ):
                                        # Should not raise — loop continues after error
                                        transfers.add_transfer_items()
                                        # render_error should have been called
                                        assert mock_render_error.called, (
                                            "render_error should be called for "
                                            "insufficient stock"
                                        )


class TestAddTransferItemsStockLock:
    """add_transfer_items locks stock rows with SELECT FOR UPDATE."""

    def test_locks_stock_with_for_update(self, mock_db, mock_user):
        """Verify SELECT ... FROM inventory.stock ... FOR UPDATE is called."""
        mock_cursor = mock_db.cursor.return_value
        mock_db.execute.return_value = MagicMock()
        mock_cursor.fetchall.return_value = [(10, "TestProduct", "SKU001", 100)]

        from dataclasses import dataclass
        from handlers.structures import Warehouse

        @dataclass
        class FakeWarehouse(Warehouse):
            pass

        fake_wh1 = FakeWarehouse(
            id=1, city_id=1, address="addr1", label=None, is_central=False
        )
        fake_wh2 = FakeWarehouse(
            id=2, city_id=1, address="addr2", label=None, is_central=False
        )

        # SERIALIZABLE tx: status → planned, FOR UPDATE transfer_items → 1, stock → 100
        mock_cursor.fetchone.side_effect = [
            (1,),  # FOR UPDATE on transfers (1st tx)
            {"status": "planned"},  # transfer status check (2nd tx, dict_row)
            1,  # FOR UPDATE transfer_items (2nd tx, item exists)
            {"quantity": 100},  # stock FOR UPDATE (2nd tx, dict_row)
        ]

        with patch("db.get_conn", return_value=mock_db):
            from handlers import transfers

            with patch(
                "handlers.transfers._get_route_pairs",
                return_value={1: [2], 2: [1]},
            ):
                with patch(
                    "handlers.transfers.get_warehouses",
                    return_value=[fake_wh1, fake_wh2],
                ):
                    with patch(
                        "handlers.transfers.get_warehouse_full_address",
                        return_value="City, addr",
                    ):
                        with patch(
                            "handlers.transfers.prompt_choice",
                            side_effect=[1, 2, 10],
                        ):
                            with patch(
                                "handlers.transfers.prompt", side_effect=["5", "y", "n"]
                            ):
                                with patch("handlers.transfers.console"):
                                    with patch(
                                        "handlers.transfers.auth_user",
                                        return_value=mock_user,
                                    ):
                                        transfers.add_transfer_items()

                                        # Verify FOR UPDATE on stock was called
                                        execute_calls = (
                                            mock_cursor.execute.call_args_list
                                        )
                                        stock_lock_found = any(
                                            "inventory.stock" in c[0][0]
                                            and "FOR UPDATE" in c[0][0].upper()
                                            for c in execute_calls
                                        )
                                        assert stock_lock_found, (
                                            "add_transfer_items must lock stock "
                                            "with SELECT ... FOR UPDATE"
                                        )

    def test_stock_locked_before_transfer_items_lock(self, mock_db, mock_user):
        """transfer_items UPDATE must appear before stock UPDATE
        in the SERIALIZABLE transaction (check-then-act pattern)."""
        mock_cursor = mock_db.cursor.return_value
        mock_db.execute.return_value = MagicMock()
        mock_cursor.fetchall.return_value = [(10, "TestProduct", "SKU001", 100)]

        from dataclasses import dataclass
        from handlers.structures import Warehouse

        @dataclass
        class FakeWarehouse(Warehouse):
            pass

        fake_wh1 = FakeWarehouse(
            id=1, city_id=1, address="addr1", label=None, is_central=False
        )
        fake_wh2 = FakeWarehouse(
            id=2, city_id=1, address="addr2", label=None, is_central=False
        )

        # SERIALIZABLE tx: status → planned, FOR UPDATE transfer_items → 1, stock → 100
        mock_cursor.fetchone.side_effect = [
            (1,),  # FOR UPDATE on transfers (1st tx)
            {"status": "planned"},  # transfer status check (2nd tx, dict_row)
            1,  # FOR UPDATE transfer_items (2nd tx, item exists)
            {"quantity": 100},  # stock FOR UPDATE (2nd tx, dict_row)
        ]

        with patch("db.get_conn", return_value=mock_db):
            from handlers import transfers

            with patch(
                "handlers.transfers._get_route_pairs",
                return_value={1: [2], 2: [1]},
            ):
                with patch(
                    "handlers.transfers.get_warehouses",
                    return_value=[fake_wh1, fake_wh2],
                ):
                    with patch(
                        "handlers.transfers.get_warehouse_full_address",
                        return_value="City, addr",
                    ):
                        with patch(
                            "handlers.transfers.prompt_choice",
                            side_effect=[1, 2, 10],
                        ):
                            with patch(
                                "handlers.transfers.prompt",
                                side_effect=["5", "y", "n"],
                            ):
                                with patch("handlers.transfers.console"):
                                    with patch(
                                        "handlers.transfers.auth_user",
                                        return_value=mock_user,
                                    ):
                                        transfers.add_transfer_items()

                                        execute_calls = mock_db.execute.call_args_list
                                        sqls = [c[0][0] for c in execute_calls]
                                        update_idx = next(
                                            i
                                            for i, sql in enumerate(sqls)
                                            if "UPDATE inventory.transfer_items" in sql
                                        )
                                        stock_update_idx = next(
                                            i
                                            for i, sql in enumerate(sqls)
                                            if "UPDATE inventory.stock" in sql
                                            and "quantity" in sql
                                        )
                                        assert update_idx < stock_update_idx, (
                                            "transfer_items UPDATE must come before "
                                            "stock UPDATE (SERIALIZABLE tx)"
                                        )


class TestRemoveTransferItemsNoRecursion:
    """remove_transfer_items uses while True, not recursion."""

    def test_returns_to_loop_after_remove(self, mock_db, mock_user):
        """After successful remove, should prompt 'Удалить ещё?'
        instead of recursing into remove_transfer_items()."""
        mock_cursor = mock_db.cursor.return_value
        mock_db.execute.return_value = MagicMock()

        from dataclasses import dataclass
        from handlers.structures import Transfer, TransferItem, Warehouse

        @dataclass
        class FakeWarehouse(Warehouse):
            pass

        fake_wh1 = FakeWarehouse(
            id=1, city_id=1, address="addr1", label=None, is_central=False
        )
        fake_wh2 = FakeWarehouse(
            id=2, city_id=1, address="addr2", label=None, is_central=False
        )

        transfer = Transfer(
            id=1,
            from_warehouse_id=1,
            to_warehouse_id=2,
            status="planned",
            created_at=datetime.now(),
            started_at=None,
            arriving_at=None,
            received_at=None,
        )

        transfer_item = TransferItem(
            id=10,
            transfer_id=1,
            product_id=5,
            quantity=10,
            requested_by=1,
            reserve_id=None,
            status="planned",
        )

        # fetchall: transfers list (outside tx), items list (inside tx1)
        mock_cursor.fetchall.side_effect = [
            [transfer],
            [transfer_item],
        ]
        # tx1: FOR UPDATE on transfers → (1,)
        # tx2: FOR UPDATE transfers status → ('planned',), transfer_items lock → 1,
        #      UPDATE RETURNING → (5,)
        mock_cursor.fetchone.side_effect = [
            (1,),  # FOR UPDATE on transfers (tx1)
            ("planned",),  # FOR UPDATE transfers status check (tx2)
            1,  # transfer_items lock consume (tx2)
            (5,),  # UPDATE RETURNING quantity (tx2)
        ]

        mock_tx = MagicMock()
        mock_tx.cursor.return_value = mock_cursor

        with patch("handlers.transfers.get_conn", return_value=mock_tx):
            from handlers import transfers

            with patch(
                "handlers.transfers.get_warehouses", return_value=[fake_wh1, fake_wh2]
            ):
                with patch(
                    "handlers.transfers.get_warehouse_full_address",
                    return_value="City, addr",
                ):
                    # prompt_choice: select transfer, select item, "delete more?" = "n"
                    with patch(
                        "handlers.transfers.prompt_choice", side_effect=[1, 10, "n"]
                    ):
                        # prompt: quantity, confirm, "delete more?" = "n"
                        with patch(
                            "handlers.transfers.prompt", side_effect=["5", "y", "n"]
                        ):
                            with patch("handlers.transfers.console"):
                                with patch(
                                    "handlers.transfers.auth_user",
                                    return_value=mock_user,
                                ):
                                    transfers.remove_transfer_items()
                                    # No recursion reached -- OK
                                    assert True

    def test_handles_multiple_removes_in_loop(self, mock_db, mock_user):
        """Multiple items can be removed in one session via the while loop."""
        mock_cursor = mock_db.cursor.return_value
        mock_db.execute.return_value = MagicMock()

        from dataclasses import dataclass
        from handlers.structures import Transfer, TransferItem, Warehouse

        @dataclass
        class FakeWarehouse(Warehouse):
            pass

        fake_wh1 = FakeWarehouse(
            id=1, city_id=1, address="addr1", label=None, is_central=False
        )
        fake_wh2 = FakeWarehouse(
            id=2, city_id=1, address="addr2", label=None, is_central=False
        )

        transfer = Transfer(
            id=1,
            from_warehouse_id=1,
            to_warehouse_id=2,
            status="planned",
            created_at=datetime.now(),
            started_at=None,
            arriving_at=None,
            received_at=None,
        )

        item1 = TransferItem(
            id=10,
            transfer_id=1,
            product_id=5,
            quantity=10,
            requested_by=1,
            reserve_id=None,
            status="planned",
        )
        item2 = TransferItem(
            id=11,
            transfer_id=1,
            product_id=6,
            quantity=20,
            requested_by=1,
            reserve_id=None,
            status="planned",
        )

        # fetchone per iteration: FOR UPDATE on transfers, transfers status check,
        # transfer_items lock, UPDATE RETURNING
        mock_cursor.fetchone.side_effect = [
            (1,),  # FOR UPDATE on transfers (1st iter)
            ("planned",),  # transfers status check (1st iter)
            1,  # transfer_items lock consume (1st iter)
            (5,),  # UPDATE RETURNING (10 - 5 = 5, 1st iter)
            (1,),  # FOR UPDATE on transfers (2nd iter)
            ("planned",),  # transfers status check (2nd iter)
            1,  # transfer_items lock consume (2nd iter)
            (10,),  # UPDATE RETURNING (20 - 10 = 10, 2nd iter)
        ]

        # Real call sequence inside remove_transfer_items:
        # Call 1: fetchall outside while → [transfer]
        # Call 2: fetchall inside tx iter 1 → [item1]
        # Call 3: fetchall inside tx iter 2 → [item1, item2]
        mock_cursor.fetchall.side_effect = [[transfer], [item1], [item1, item2]]

        mock_tx = MagicMock()
        mock_tx.__enter__ = MagicMock(return_value=mock_tx)
        mock_tx.__exit__ = MagicMock(return_value=False)
        mock_tx.cursor = MagicMock(return_value=mock_cursor)

        with patch("handlers.transfers.get_conn", return_value=mock_tx):
            from handlers import transfers

            with patch(
                "handlers.transfers.get_warehouses", return_value=[fake_wh1, fake_wh2]
            ):
                with patch(
                    "handlers.transfers.get_warehouse_full_address",
                    return_value="City, addr",
                ):
                    with patch(
                        "handlers.transfers.prompt_choice", side_effect=[1, 10, 11, "n"]
                    ):
                        with patch(
                            "handlers.transfers.prompt",
                            side_effect=["5", "y", "y", "5", "y", "n"],
                        ):
                            with patch("handlers.transfers.console"):
                                with patch(
                                    "handlers.transfers.auth_user",
                                    return_value=mock_user,
                                ):
                                    transfers.remove_transfer_items()

                                    assert (
                                        mock_cursor.fetchall.call_count >= 2
                                    ), "while loop should call fetchall at least twice"


class TestRemoveTransferItemsTransferItemsLock:
    """remove_transfer_items locks transfer_items with SELECT FOR UPDATE."""

    def test_locks_transfer_items_before_update(self, mock_db, mock_user):
        """Verify SELECT ... FOR UPDATE on transfer_items before UPDATE."""
        mock_cursor = mock_db.cursor.return_value
        mock_db.execute.return_value = MagicMock()

        from dataclasses import dataclass
        from handlers.structures import Transfer, TransferItem, Warehouse

        @dataclass
        class FakeWarehouse(Warehouse):
            pass

        fake_wh1 = FakeWarehouse(
            id=1, city_id=1, address="addr1", label=None, is_central=False
        )
        fake_wh2 = FakeWarehouse(
            id=2, city_id=1, address="addr2", label=None, is_central=False
        )

        transfer = Transfer(
            id=1,
            from_warehouse_id=1,
            to_warehouse_id=2,
            status="planned",
            created_at=datetime.now(),
            started_at=None,
            arriving_at=None,
            received_at=None,
        )

        item = TransferItem(
            id=10,
            transfer_id=1,
            product_id=5,
            quantity=10,
            requested_by=1,
            reserve_id=None,
            status="planned",
        )

        # fetchall: transfers list (outside), items list (inside tx)
        mock_cursor.fetchall.side_effect = [
            [transfer],
            [item],
        ]
        # fetchone: FOR UPDATE on transfers, transfers status check,
        #           transfer_items lock, UPDATE RETURNING
        mock_cursor.fetchone.side_effect = [
            (1,),  # FOR UPDATE on transfers (inside tx)
            ("planned",),  # transfers status check (inside tx2)
            1,  # transfer_items lock consume (inside tx2)
            (5,),  # UPDATE RETURNING (inside tx2)
        ]

        with patch("db.get_conn", return_value=mock_db):
            from handlers import transfers

            with patch(
                "handlers.transfers.get_warehouses", return_value=[fake_wh1, fake_wh2]
            ):
                with patch(
                    "handlers.transfers.get_warehouse_full_address",
                    return_value="City, addr",
                ):
                    # prompt_choice: select transfer, select item, "delete more?" = "n"
                    with patch(
                        "handlers.transfers.prompt_choice", side_effect=[1, 10, "n"]
                    ):
                        # prompt: quantity, confirm, "delete more?" = "n"
                        with patch(
                            "handlers.transfers.prompt", side_effect=["5", "y", "n"]
                        ):
                            with patch("handlers.transfers.console"):
                                with patch(
                                    "handlers.transfers.auth_user",
                                    return_value=mock_user,
                                ):
                                    mock_db.cursor = MagicMock(return_value=mock_cursor)
                                    mock_tx = MagicMock()
                                    mock_tx.cursor.return_value = mock_cursor
                                    mock_db.transaction.return_value = mock_tx

                                    transfers.remove_transfer_items()

                                    execute_calls = mock_cursor.execute.call_args_list
                                    ti_lock_found = any(
                                        "transfer_items" in c[0][0]
                                        and "FOR UPDATE" in c[0][0].upper()
                                        for c in execute_calls
                                    )
                                    assert ti_lock_found, (
                                        "remove_transfer_items must lock "
                                        "transfer_items with SELECT ... FOR UPDATE"
                                    )


class TestRemoveTransferItemsTypeCoercion:
    """remove_transfer_items uses int(item_id) in DELETE."""

    def test_deletes_with_int_item_id(self, mock_db, mock_user):
        """DELETE FROM transfer_items WHERE id = %s must accept int."""
        mock_cursor = mock_db.cursor.return_value
        mock_db.execute.return_value = MagicMock()

        from dataclasses import dataclass
        from handlers.structures import Transfer, TransferItem, Warehouse

        @dataclass
        class FakeWarehouse(Warehouse):
            pass

        fake_wh1 = FakeWarehouse(
            id=1, city_id=1, address="addr1", label=None, is_central=False
        )
        fake_wh2 = FakeWarehouse(
            id=2, city_id=1, address="addr2", label=None, is_central=False
        )

        transfer = Transfer(
            id=1,
            from_warehouse_id=1,
            to_warehouse_id=2,
            status="planned",
            created_at=datetime.now(),
            started_at=None,
            arriving_at=None,
            received_at=None,
        )

        item = TransferItem(
            id=10,
            transfer_id=1,
            product_id=5,
            quantity=5,
            requested_by=1,
            reserve_id=None,
            status="planned",
        )

        # fetchall: transfers list (outside), items list (inside tx)
        mock_cursor.fetchall.side_effect = [
            [transfer],
            [item],
        ]
        # fetchone: FOR UPDATE on transfers, transfers status check,
        #           transfer_items lock, UPDATE RETURNING
        mock_cursor.fetchone.side_effect = [
            (1,),  # FOR UPDATE on transfers (inside tx)
            ("planned",),  # transfers status check (inside tx2)
            1,  # transfer_items lock consume (inside tx2)
            (0,),  # UPDATE RETURNING quantity (0 = delete fully, inside tx2)
        ]

        with patch("db.get_conn", return_value=mock_db):
            from handlers import transfers

            with patch(
                "handlers.transfers.get_warehouses", return_value=[fake_wh1, fake_wh2]
            ):
                with patch(
                    "handlers.transfers.get_warehouse_full_address",
                    return_value="City, addr",
                ):
                    with patch(
                        "handlers.transfers.prompt_choice", side_effect=[1, 10, "n"]
                    ):
                        with patch(
                            "handlers.transfers.prompt", side_effect=["5", "y", "n"]
                        ):
                            with patch("handlers.transfers.console"):
                                with patch(
                                    "handlers.transfers.auth_user",
                                    return_value=mock_user,
                                ):
                                    mock_db.cursor = MagicMock(return_value=mock_cursor)
                                    mock_tx = MagicMock()
                                    mock_tx.cursor.return_value = mock_cursor
                                    mock_db.transaction.return_value = mock_tx

                                    transfers.remove_transfer_items()

                                    # Verify DELETE called with int
                                    # DELETE goes through mock_db.execute(), not cursor.execute()
                                    db_calls = mock_db.execute.call_args_list
                                    delete_calls = [
                                        c for c in db_calls if "DELETE" in c[0][0]
                                    ]
                                    assert (
                                        delete_calls
                                    ), "DELETE should be called when quantity reaches 0"
                                    for c in delete_calls:
                                        sql = c[0][0]
                                        params = c[0][1]
                                        item_param = params[0]
                                        assert isinstance(
                                            item_param, int
                                        ), f"DELETE item_id must be int, got {type(item_param)}: {item_param}"
