"""Unit tests for order_items handlers (handlers/order_items.py).

Covers helper functions (get_order_by_id, check_order, get_sku,
get_order_items, is_product_in_order). Mutation commands (add, edit, delete)
require interactive prompt mocking and are tested separately.
"""

from unittest.mock import MagicMock, patch

import pytest


class TestGetSku:
    """get_sku() parses SKU from 'Name (SKU)' format."""

    def test_parses_valid_input(self):
        from handlers.order_items import get_sku

        assert get_sku("Молоко (MLK-001)") == "MLK-001"

    def test_parses_empty_parens_returns_empty_string(self):
        from handlers.order_items import get_sku

        assert get_sku("()") == ""

    def test_returns_none_when_no_parens(self):
        from handlers.order_items import get_sku

        assert get_sku("Просто название") is None

    def test_returns_none_when_only_open_paren(self):
        from handlers.order_items import get_sku

        assert get_sku("Название (SKU") is None

    def test_returns_none_when_empty_string(self):
        from handlers.order_items import get_sku

        assert get_sku("") is None


class TestIsProductInOrder:
    """is_product_in_order() checks product membership in order items."""

    def test_returns_true_when_product_exists(self):
        from handlers.order_items import is_product_in_order
        from handlers.structures import OrderItem, Product
        from decimal import Decimal

        item = OrderItem(order_id=1, product_id=5, quantity=2, price=Decimal("100"))
        product = Product(
            id=5, sku="SKU-5", name="Товар", price=Decimal("100"), category_id=1
        )

        assert is_product_in_order([item], product) is True

    def test_returns_false_when_product_not_in_list(self):
        from handlers.order_items import is_product_in_order
        from handlers.structures import OrderItem, Product
        from decimal import Decimal

        item = OrderItem(order_id=1, product_id=5, quantity=2, price=Decimal("100"))
        product = Product(
            id=99, sku="SKU-99", name="Другой", price=Decimal("200"), category_id=2
        )

        assert is_product_in_order([item], product) is False

    def test_returns_false_for_empty_items_list(self):
        from handlers.order_items import is_product_in_order
        from handlers.structures import Product
        from decimal import Decimal

        product = Product(
            id=1, sku="SKU-1", name="Товар", price=Decimal("50"), category_id=1
        )

        assert is_product_in_order([], product) is False


class TestGetOrderById:
    """get_order_by_id() maps a row to an Order dataclass."""

    def test_finds_existing_order(self, mock_db, mock_user):
        from handlers.structures import Order
        from datetime import datetime
        from decimal import Decimal

        order_data = Order(
            id=1,
            status="unpublished",
            total_amount=Decimal("0"),
            created_at=datetime.now(),
            warehouse_id=1,
            created_by_id=1,
        )

        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = order_data

        with patch("db.get_conn", return_value=mock_db):
            from handlers import order_items  # noqa: F811

            result = order_items.get_order_by_id(1)
            assert result is not None
            assert result.id == 1
            assert result.status == "unpublished"

    def test_returns_none_for_unknown_id(self, mock_db, mock_user):
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = None

        with patch("db.get_conn", return_value=mock_db):
            from handlers import order_items  # noqa: F811

            result = order_items.get_order_by_id(999)
            assert result is None


class TestCheckOrder:
    """check_order() validates an order is editable."""

    def test_returns_false_when_order_not_found(self, mock_db, mock_user):
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = None

        with patch("db.get_conn", return_value=mock_db):
            from handlers import order_items  # noqa: F811

            with patch("handlers.order_items.render_error") as mock_error:
                result = order_items.check_order(999)
                assert result is False
                mock_error.assert_called_once()

    def test_returns_false_when_order_published(self, mock_db, mock_user):
        from handlers.structures import Order
        from datetime import datetime
        from decimal import Decimal

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
            from handlers import order_items  # noqa: F811

            with patch("handlers.order_items.render_error") as mock_error:
                result = order_items.check_order(1)
                assert result is False
                mock_error.assert_called_once()
                assert "опубликован" in mock_error.call_args[0][0]

    def test_returns_true_when_order_unpublished(self, mock_db, mock_user):
        from handlers.structures import Order
        from datetime import datetime
        from decimal import Decimal

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
            from handlers import order_items  # noqa: F811

            result = order_items.check_order(1)
            assert result is True


class TestGetOrderItems:
    """get_order_items() returns a list of OrderItem objects for an order."""

    def test_returns_list_of_items(self, mock_db, mock_user):
        from handlers.structures import OrderItem
        from decimal import Decimal

        item1 = OrderItem(order_id=1, product_id=2, quantity=3, price=Decimal("50"))
        item2 = OrderItem(order_id=1, product_id=7, quantity=1, price=Decimal("200"))

        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchall.return_value = [item1, item2]

        with patch("db.get_conn", return_value=mock_db):
            from handlers import order_items  # noqa: F811

            result = order_items.get_order_items(1)
            assert len(result) == 2
            assert result[0].product_id == 2
            assert result[1].quantity == 1

    def test_returns_empty_list_when_no_items(self, mock_db, mock_user):
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchall.return_value = []

        with patch("db.get_conn", return_value=mock_db):
            from handlers import order_items  # noqa: F811

            result = order_items.get_order_items(999)
            assert result == []


# ─── add_order_item ───────────────────────────────────────────────────


class TestAddOrderItem:
    """add_order_item() adds items to an unpublished order."""

    def test_returns_error_when_order_not_found(self, mock_db, mock_user):
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = None

        with patch("db.get_conn", return_value=mock_db):
            from handlers import order_items  # noqa: F811

            with patch("handlers.order_items.render_error") as mock_error:
                order_items.add_order_item(999)
                mock_error.assert_called_once()
                assert "Нет заказа" in mock_error.call_args[0][0]

    def test_returns_error_when_order_published(self, mock_db, mock_user):
        from handlers.structures import Order
        from datetime import datetime
        from decimal import Decimal

        order_data = Order(
            id=1,
            status="new",
            total_amount=Decimal("100"),
            created_at=datetime.now(),
            warehouse_id=1,
            created_by_id=1,
        )

        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.side_effect = [order_data, None]

        with patch("db.get_conn", return_value=mock_db):
            from handlers import order_items  # noqa: F811

            with patch("handlers.order_items.render_error") as mock_error:
                order_items.add_order_item(1)
                mock_error.assert_called_once()
                assert "опубликован" in mock_error.call_args[0][0]

    def test_returns_error_when_no_products_left(self, mock_db, mock_user):
        from handlers.structures import Order, OrderItem, Product
        from datetime import datetime
        from decimal import Decimal

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
        mock_cursor.fetchall.return_value = []

        with patch("db.get_conn", return_value=mock_db):
            from handlers import order_items  # noqa: F811

            with patch("handlers.order_items.get_products") as mock_products:
                mock_products.return_value = [
                    Product(id=1, sku="S1", name="Продукт", price=Decimal("10"), category_id=1)
                ]
                with patch("handlers.order_items.get_order_items") as mock_items:
                    mock_items.return_value = [
                        OrderItem(order_id=1, product_id=1, quantity=1, price=Decimal("10"))
                    ]
                    with patch("handlers.order_items.render_error") as mock_error:
                        order_items.add_order_item(1)
                        mock_error.assert_called_once()
                        assert "Нет товаров" in mock_error.call_args[0][0]

    @patch("handlers.order_items.console")
    @patch("handlers.order_items.YesNoValidator")
    @patch("handlers.order_items.prompt", side_effect=["Товар (S5)", "2", "нет"])
    @patch("handlers.order_items.get_product_by_sku")
    @patch("handlers.order_items.get_order_items")
    @patch("handlers.order_items.get_products")
    def test_inserts_item_and_updates_total(
        self,
        mock_products,
        mock_items,
        mock_product_by_sku,
        mock_prompt,
        mock_ynn,
        mock_console,
        mock_db,
        mock_user,
    ):
        from handlers.structures import Order, Product
        from datetime import datetime
        from decimal import Decimal

        order_data = Order(
            id=1,
            status="unpublished",
            total_amount=Decimal("100"),
            created_at=datetime.now(),
            warehouse_id=1,
            created_by_id=1,
        )

        from handlers.structures import OrderItem

        mock_cursor = mock_db.cursor.return_value
        mock_cursor.execute.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [
            OrderItem(
                order_id=1, product_id=5, quantity=2, price=Decimal("25")
            ),  # INSERT RETURNING *
        ]

        with patch("db.get_conn", return_value=mock_db):
            from handlers import order_items  # noqa: F811

            mock_tx = MagicMock()
            mock_tx.__enter__ = MagicMock(return_value=None)
            mock_tx.__exit__ = MagicMock(return_value=False)
            mock_db.transaction = MagicMock(return_value=mock_tx)

            # Patch get_order_by_id directly — check_order() and line 136
            # both call it, and they use conn.cursor().fetchone() which would
            # consume the side_effect list meant for the INSERT RETURNING.
            with patch("handlers.order_items.get_order_by_id", return_value=order_data):
                mock_products.return_value = [
                    Product(id=5, sku="S5", name="Товар", price=Decimal("25"), category_id=1),
                ]
                mock_product_by_sku.return_value = Product(
                    id=5, sku="S5", name="Товар", price=Decimal("25"), category_id=1
                )
                mock_items.return_value = []
                mock_ynn.is_yes = MagicMock(side_effect=[False])

                order_items.add_order_item(1)

            # INSERT executed on cursor
            insert_calls = [
                c
                for c in mock_cursor.execute.call_args_list
                if "INSERT" in c[0][0]
            ]
            assert len(insert_calls) >= 1

            # UPDATE total_amount executed on db
            update_total_calls = [
                c
                for c in mock_db.execute.call_args_list
                if "UPDATE sales.orders SET total_amount" in c[0][0]
            ]
            assert len(update_total_calls) >= 1

    def test_recurses_when_user_wants_more(self, mock_db, mock_user):
        from handlers.structures import Order, Product, OrderItem
        from datetime import datetime
        from decimal import Decimal

        order_data = Order(
            id=1,
            status="unpublished",
            total_amount=Decimal("100"),
            created_at=datetime.now(),
            warehouse_id=1,
            created_by_id=1,
        )

        mock_cursor = mock_db.cursor.return_value
        mock_cursor.execute.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [
            OrderItem(
                order_id=1, product_id=5, quantity=2, price=Decimal("25")
            ),  # INSERT RETURNING *
        ]

        with patch("db.get_conn", return_value=mock_db):
            from handlers import order_items  # noqa: F811

            mock_tx = MagicMock()
            mock_tx.__enter__ = MagicMock(return_value=None)
            mock_tx.__exit__ = MagicMock(return_value=False)
            mock_db.transaction = MagicMock(return_value=mock_tx)

            # Patch get_order_by_id directly — check_order() calls it
            with patch("handlers.order_items.get_order_by_id", return_value=order_data):
                with patch("handlers.order_items.get_products") as mock_products:
                    # First call: one product available; recursive call (after "да"): no products → exits
                    mock_products.side_effect = [
                        [Product(id=5, sku="S5", name="Товар", price=Decimal("25"), category_id=1)],
                        [],
                    ]
                    with patch("handlers.order_items.get_product_by_sku") as mock_sku:
                        mock_sku.return_value = Product(
                            id=5, sku="S5", name="Товар", price=Decimal("25"), category_id=1
                        )
                        with patch("handlers.order_items.get_order_items") as mock_items:
                            mock_items.return_value = []
                            with patch(
                                "handlers.order_items.prompt",
                                side_effect=["Товар (S5)", "2", "да"],
                            ):
                                with patch("handlers.order_items.YesNoValidator") as mock_ynn:
                                    # First call: user wants more → True
                                    mock_ynn.is_yes = MagicMock(side_effect=[True])
                                    with patch("handlers.order_items.console"):
                                        order_items.add_order_item(1)
                                        mock_ynn.is_yes.assert_called()


# ─── edit_order_item ──────────────────────────────────────────────────


class TestEditOrderItem:
    """edit_order_item() modifies an existing order item."""

    def test_returns_error_when_order_not_found(self, mock_db, mock_user):
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = None

        with patch("db.get_conn", return_value=mock_db):
            from handlers import order_items  # noqa: F811

            with patch("handlers.order_items.render_error") as mock_error:
                order_items.edit_order_item(999)
                mock_error.assert_called_once()

    def test_returns_error_when_no_items_in_order(self, mock_db, mock_user):
        from handlers.structures import Order
        from datetime import datetime
        from decimal import Decimal

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
        mock_cursor.fetchall.return_value = []

        with patch("db.get_conn", return_value=mock_db):
            from handlers import order_items  # noqa: F811

            with patch("handlers.order_items.render_error") as mock_error:
                order_items.edit_order_item(1)
                mock_error.assert_called_once()
                assert "нет товаров" in mock_error.call_args[0][0]

    def test_updates_quantity_and_total(self, mock_db, mock_user):
        from handlers.structures import Order, Product, OrderItem
        from datetime import datetime
        from decimal import Decimal

        order_data = Order(
            id=1,
            status="unpublished",
            total_amount=Decimal("200"),
            created_at=datetime.now(),
            warehouse_id=1,
            created_by_id=1,
        )

        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.side_effect = [
            OrderItem(order_id=1, product_id=5, quantity=2, price=Decimal("100")),
        ]

        with patch("db.get_conn", return_value=mock_db):
            from handlers import order_items  # noqa: F811

            mock_tx = MagicMock()
            mock_tx.__enter__ = MagicMock(return_value=None)
            mock_tx.__exit__ = MagicMock(return_value=False)
            mock_db.transaction = MagicMock(return_value=mock_tx)

            # Patch get_order_by_id — check_order() and line 196 both call it
            with patch("handlers.order_items.get_order_by_id", return_value=order_data):
                with patch("handlers.order_items.get_order_items") as mock_items:
                    mock_items.return_value = [
                        OrderItem(order_id=1, product_id=5, quantity=2, price=Decimal("100"))
                    ]
                    with patch("handlers.order_items.get_product_by_id") as mock_prod:
                        mock_prod.return_value = Product(id=5, sku="S5", name="Товар", price=Decimal("75"), category_id=1)
                        with patch("handlers.order_items.choice", return_value=5):
                            with patch("handlers.order_items.prompt", return_value="1"):
                                with patch("handlers.order_items.console"):
                                    order_items.edit_order_item(1)

                                    # UPDATE order_items executed
                                    update_item_calls = [
                                        c
                                        for c in mock_db.execute.call_args_list
                                        if "UPDATE sales.order_items" in c[0][0]
                                    ]
                                    assert len(update_item_calls) >= 1

                                    # UPDATE total_amount executed
                                    update_total_calls = [
                                        c
                                        for c in mock_db.execute.call_args_list
                                        if "UPDATE sales.orders SET total_amount" in c[0][0]
                                    ]
                                assert len(update_total_calls) >= 1


# ─── delete_order_item ────────────────────────────────────────────────


class TestDeleteOrderItem:
    """delete_order_item() removes an item from an unpublished order."""

    def test_returns_error_when_order_not_found(self, mock_db, mock_user):
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = None

        with patch("db.get_conn", return_value=mock_db):
            from handlers import order_items  # noqa: F811

            with patch("handlers.order_items.render_error") as mock_error:
                order_items.delete_order_item(999)
                mock_error.assert_called_once()

    def test_returns_error_when_no_items_in_order(self, mock_db, mock_user):
        from handlers.structures import Order
        from datetime import datetime
        from decimal import Decimal

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
        mock_cursor.fetchall.return_value = []

        with patch("db.get_conn", return_value=mock_db):
            from handlers import order_items  # noqa: F811

            with patch("handlers.order_items.render_error") as mock_error:
                order_items.delete_order_item(1)
                mock_error.assert_called_once()
                assert "нет товаров" in mock_error.call_args[0][0]

    def test_cancels_on_no_confirmation(self, mock_db, mock_user):
        from handlers.structures import Order, OrderItem, Product
        from datetime import datetime
        from decimal import Decimal

        order_data = Order(
            id=1,
            status="unpublished",
            total_amount=Decimal("200"),
            created_at=datetime.now(),
            warehouse_id=1,
            created_by_id=1,
        )

        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = order_data
        mock_cursor.fetchall.return_value = [
            OrderItem(order_id=1, product_id=5, quantity=2, price=Decimal("100"))
        ]

        with patch("db.get_conn", return_value=mock_db):
            from handlers import order_items  # noqa: F811

            with patch("handlers.order_items.get_product_by_id") as mock_prod:
                mock_prod.return_value = Product(id=5, sku="S5", name="Товар", price=Decimal("100"), category_id=1)
                with patch("handlers.order_items.choice", return_value=5):
                    with patch("handlers.order_items._render_order_item"):
                        with patch("handlers.order_items.prompt", return_value="n"):
                            with patch("handlers.order_items.console") as mock_console:
                                order_items.delete_order_item(1)

                                # No DELETE executed
                                delete_calls = [
                                    c
                                    for c in mock_db.execute.call_args_list
                                    if "DELETE" in c[0][0]
                                ]
                                assert len(delete_calls) == 0

    def test_deletes_item_and_updates_total(self, mock_db, mock_user):
        from handlers.structures import Order, OrderItem, Product
        from datetime import datetime
        from decimal import Decimal

        order_data = Order(
            id=1,
            status="unpublished",
            total_amount=Decimal("200"),
            created_at=datetime.now(),
            warehouse_id=1,
            created_by_id=1,
        )

        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.side_effect = [
            order_data,  # check_order → get_order_by_id
            OrderItem(order_id=1, product_id=5, quantity=2, price=Decimal("100")),  # get item
            Order(  # get_order_by_id after delete
                id=1,
                status="unpublished",
                total_amount=Decimal("0"),
                created_at=datetime.now(),
                warehouse_id=1,
                created_by_id=1,
            ),
        ]

        with patch("db.get_conn", return_value=mock_db):
            from handlers import order_items  # noqa: F811

            mock_tx = MagicMock()
            mock_tx.__enter__ = MagicMock(return_value=None)
            mock_tx.__exit__ = MagicMock(return_value=False)
            mock_db.transaction = MagicMock(return_value=mock_tx)

            with patch("handlers.order_items.get_order_items") as mock_items:
                mock_items.return_value = [
                    OrderItem(order_id=1, product_id=5, quantity=2, price=Decimal("100"))
                ]
                with patch("handlers.order_items.get_product_by_id") as mock_prod:
                    mock_prod.return_value = Product(id=5, sku="S5", name="Товар", price=Decimal("100"), category_id=1)
                    with patch("handlers.order_items.choice", return_value=5):
                        with patch("handlers.order_items._render_order_item"):
                            with patch("handlers.order_items.prompt", return_value="y"):
                                with patch("handlers.order_items.console"):
                                    order_items.delete_order_item(1)

                                    # DELETE executed
                                    delete_calls = [
                                        c
                                        for c in mock_db.execute.call_args_list
                                        if "DELETE" in c[0][0]
                                    ]
                                    assert len(delete_calls) >= 1

                                    # UPDATE total_amount executed
                                    update_total_calls = [
                                        c
                                        for c in mock_db.execute.call_args_list
                                        if "UPDATE sales.orders SET total_amount" in c[0][0]
                                    ]
                                    assert len(update_total_calls) >= 1
