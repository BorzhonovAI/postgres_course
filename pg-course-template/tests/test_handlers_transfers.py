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
        # Provide actual stock data so the while loop doesn't break
        mock_cursor.fetchall.return_value = [(10, "TestProduct", "SKU001", 100)]

        from dataclasses import dataclass
        from handlers.structures import Warehouse

        @dataclass
        class FakeWarehouse(Warehouse):
            pass

        fake_wh1 = FakeWarehouse(id=1, city_id=1, address="addr1", label=None, is_central=False)
        fake_wh2 = FakeWarehouse(id=2, city_id=1, address="addr2", label=None, is_central=False)

        # Set up all side effects on mock_cursor.fetchone
        # 1. FOR UPDATE on transfers: existing transfer found
        # 2. Stock check: quantity = 100
        # 3. Transfer items lock: row exists (consume)
        mock_cursor.fetchone.side_effect = [
            (1,),        # FOR UPDATE on transfers
            (100,),      # stock check quantity
            (1,),        # transfer_items lock consume
        ]

        with patch("db.get_conn", return_value=mock_db):
            from handlers import transfers

            with patch("handlers.transfers.get_warehouses", return_value=[fake_wh1, fake_wh2]):
                with patch("handlers.transfers.get_warehouse_full_address",
                           return_value="City, addr"):
                    # prompt_choice sequence: from_wh, to_wh, product, confirm, add_more
                    with patch("handlers.transfers.prompt_choice",
                               side_effect=[1, 2, 10, "y", "n"]):
                        with patch("handlers.transfers.prompt",
                                   side_effect=["5", "y", "n"]):
                            with patch("handlers.transfers.console"):
                                with patch("handlers.transfers.auth_user",
                                           return_value=mock_user):
                                    # Patch ALL cursor() calls to return mock_cursor
                                    mock_db.cursor = MagicMock(return_value=mock_cursor)
                                    mock_tx = MagicMock()
                                    mock_tx.cursor.return_value = mock_cursor
                                    mock_db.transaction.return_value = mock_tx

                                    try:
                                        transfers.add_transfer_items()
                                    except Exception as e:
                                        print(f"\nERROR: {type(e).__name__}: {e}")
                                        import traceback
                                        traceback.print_exc()

                                    # Verify FOR UPDATE on transfer_items was called
                                    execute_calls = mock_cursor.execute.call_args_list
                                    print("\n=== ALL EXECUTE CALLS ON mock_cursor ===")
                                    for i, c in enumerate(execute_calls):
                                        sql = c[0][0]
                                        print(f"{i}: LEN={len(sql)} — {sql[:120]}")
                                    print(f"=== mock_cursor.fetchone.call_count: {mock_cursor.fetchone.call_count} ===")
                                    print(f"=== mock_db.execute.call_count: {mock_db.execute.call_count} ===")
                                    for i, c in enumerate(mock_db.execute.call_args_list):
                                        sql = c[0][0]
                                        print(f"db {i}: LEN={len(sql)} — {sql[:120]}")

                                    found = False
                                    for call in execute_calls:
                                        sql = call[0][0]
                                        if ("transfer_items" in sql
                                                and "FOR UPDATE" in sql.upper()):
                                            found = True
                                            break
                                    assert found, (
                                        "add_transfer_items must lock transfer_items "
                                        "with SELECT ... FOR UPDATE before INSERT"
                                    )


class TestAddTransferItemsInsufficientStock:
    """add_transfer_items rejects quantity > stock quantity."""

    def test_rejects_excessive_quantity(self, mock_db, mock_user):
        """When requested quantity exceeds stock, print error and continue."""
        mock_cursor = mock_db.cursor.return_value
        mock_db.execute.return_value = MagicMock()
        # Provide actual stock data so the while loop doesn't break
        mock_cursor.fetchall.return_value = [(10, "TestProduct", "SKU001", 2)]

        from dataclasses import dataclass
        from handlers.structures import Warehouse

        @dataclass
        class FakeWarehouse(Warehouse):
            pass

        fake_wh1 = FakeWarehouse(id=1, city_id=1, address="addr1", label=None, is_central=False)
        fake_wh2 = FakeWarehouse(id=2, city_id=1, address="addr2", label=None, is_central=False)

        # flow: FOR UPDATE (1), stock check (2), then cancel
        mock_cursor.fetchone.side_effect = [
            (1,),  # FOR UPDATE: row found
            (2,),  # stock check: quantity = 2
        ]

        with patch("db.get_conn", return_value=mock_db):
            from handlers import transfers

            with patch("handlers.transfers.get_warehouses", return_value=[fake_wh1, fake_wh2]):
                with patch("handlers.transfers.get_warehouse_full_address",
                           return_value="City, addr"):
                    # from_wh, to_wh, product, cancel
                    with patch("handlers.transfers.prompt_choice",
                               side_effect=[1, 2, 10, None]):
                        # quantity, answer (add_more not reached)
                        with patch("handlers.transfers.prompt",
                                   side_effect=["5", "y"]):
                            with patch("handlers.transfers.render_error") as mock_render_error:
                                with patch("handlers.transfers.auth_user",
                                           return_value=mock_user):
                                    mock_db.cursor = MagicMock(return_value=mock_cursor)
                                    mock_tx = MagicMock()
                                    mock_tx.cursor.return_value = mock_cursor
                                    mock_db.transaction.return_value = mock_tx

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
            (1,),  # FOR UPDATE: row found
            (1,),  # stock check: quantity = 1
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

        fake_wh1 = FakeWarehouse(id=1, city_id=1, address="addr1", label=None, is_central=False)
        fake_wh2 = FakeWarehouse(id=2, city_id=1, address="addr2", label=None, is_central=False)

        with patch("db.get_conn", return_value=mock_db):
            from handlers import transfers

            with patch("handlers.transfers.get_warehouses", return_value=[fake_wh1, fake_wh2]):
                with patch("handlers.transfers.get_warehouse_full_address",
                           return_value="City, addr"):
                    # from_wh, to_wh, product1, cancel
                    with patch("handlers.transfers.prompt_choice",
                               side_effect=[1, 2, 10, None]):
                        # quantity, answer
                        with patch("handlers.transfers.prompt",
                                   side_effect=["5", "y"]):
                            with patch("handlers.transfers.render_error") as mock_render_error:
                                with patch("handlers.transfers.auth_user",
                                           return_value=mock_user):
                                    # Should not raise — loop continues after error
                                    transfers.add_transfer_items()
                                    # render_error should have been called
                                    assert mock_render_error.called, (
                                        "render_error should be called for "
                                        "insufficient stock"
                                    )
