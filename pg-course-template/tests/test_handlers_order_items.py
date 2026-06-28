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
        product = Product(id=5, sku="SKU-5", name="Товар", price=Decimal("100"), category_id=1)

        assert is_product_in_order([item], product) is True

    def test_returns_false_when_product_not_in_list(self):
        from handlers.order_items import is_product_in_order
        from handlers.structures import OrderItem, Product
        from decimal import Decimal

        item = OrderItem(order_id=1, product_id=5, quantity=2, price=Decimal("100"))
        product = Product(id=99, sku="SKU-99", name="Другой", price=Decimal("200"), category_id=2)

        assert is_product_in_order([item], product) is False

    def test_returns_false_for_empty_items_list(self):
        from handlers.order_items import is_product_in_order
        from handlers.structures import Product
        from decimal import Decimal

        product = Product(id=1, sku="SKU-1", name="Товар", price=Decimal("50"), category_id=1)

        assert is_product_in_order([], product) is False


class TestGetOrderById:
    """get_order_by_id() maps a row to an Order dataclass."""

    def test_finds_existing_order(self, mock_db, mock_user):
        from handlers.structures import Order
        from datetime import datetime
        from decimal import Decimal

        order_data = Order(
            id=1, status="unpublished", total_amount=Decimal("0"),
            created_at=datetime.now(), warehouse_id=1, created_by_id=1
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
            id=1, status="new", total_amount=Decimal("500"),
            created_at=datetime.now(), warehouse_id=1, created_by_id=1
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
            id=1, status="unpublished", total_amount=Decimal("100"),
            created_at=datetime.now(), warehouse_id=1, created_by_id=1
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
