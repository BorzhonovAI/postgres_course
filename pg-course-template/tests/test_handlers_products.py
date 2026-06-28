"""Unit tests for product handlers (handlers/products.py).

Covers helper functions (get_product_by_id, get_product_by_sku, get_product_by_name,
products_count, get_products) and commands (show_product, delete_product FK-protection).
Mutation commands that require interactive prompt mocking are tested separately.
"""

from unittest.mock import MagicMock, patch

import pytest


class TestGetProductById:
    """get_product_by_id() maps a row to a Product dataclass."""

    def test_finds_existing_product(self, mock_db, mock_user):
        from handlers.structures import Product

        product_data = Product(
            id=1, sku="ABC-001", name="Видеокарта", price="299.99", category_id=1
        )

        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = product_data

        with patch("db.get_conn", return_value=mock_db):
            from handlers import products  # noqa: F811

            result = products.get_product_by_id(1)
            assert result is not None
            assert result.id == 1
            assert result.name == "Видеокарта"
            assert result.sku == "ABC-001"

    def test_returns_none_for_unknown_id(self, mock_db, mock_user):
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = None

        with patch("db.get_conn", return_value=mock_db):
            from handlers import products  # noqa: F811

            result = products.get_product_by_id(999)
            assert result is None


class TestGetProductBySku:
    """get_product_by_sku() looks up a product by its SKU."""

    def test_finds_existing_product(self, mock_db, mock_user):
        from handlers.structures import Product

        product_data = Product(
            id=5, sku="XYZ-999", name="Клавиатура", price="49.99", category_id=2
        )

        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = product_data

        with patch("db.get_conn", return_value=mock_db):
            from handlers import products  # noqa: F811

            result = products.get_product_by_sku("XYZ-999")
            assert result is not None
            assert result.id == 5
            assert result.name == "Клавиатура"

    def test_returns_none_for_unknown_sku(self, mock_db, mock_user):
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = None

        with patch("db.get_conn", return_value=mock_db):
            from handlers import products  # noqa: F811

            result = products.get_product_by_sku("NOPE")
            assert result is None


class TestGetProductByName:
    """get_product_by_name() looks up a product by its name."""

    def test_finds_existing_product(self, mock_db, mock_user):
        from handlers.structures import Product

        product_data = Product(
            id=3, sku="MSE-042", name="Мышь", price="19.99", category_id=2
        )

        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = product_data

        with patch("db.get_conn", return_value=mock_db):
            from handlers import products  # noqa: F811

            result = products.get_product_by_name("Мышь")
            assert result is not None
            assert result.id == 3
            assert result.sku == "MSE-042"

    def test_returns_none_for_unknown_name(self, mock_db, mock_user):
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = None

        with patch("db.get_conn", return_value=mock_db):
            from handlers import products  # noqa: F811

            result = products.get_product_by_name("Несуществующий")
            assert result is None


class TestProductsCount:
    """products_count() returns the row count from catalog.products."""

    def test_returns_integer_count(self, mock_db, mock_user):
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = (12,)

        with patch("db.get_conn", return_value=mock_db):
            from handlers import products  # noqa: F811

            count = products.products_count()
            assert count == 12


class TestGetProducts:
    """get_products() returns a list of all Product objects."""

    def test_returns_list_of_products(self, mock_db, mock_user):
        from handlers.structures import Product

        p1 = Product(id=1, sku="A", name="Продукт A", price="10.00", category_id=1)
        p2 = Product(id=2, sku="B", name="Продукт B", price="20.00", category_id=2)

        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchall.return_value = [p1, p2]

        with patch("db.get_conn", return_value=mock_db):
            from handlers import products  # noqa: F811

            result = products.get_products()
            assert len(result) == 2
            assert result[0].id == 1
            assert result[1].name == "Продукт B"


class TestShowProduct:
    """show_product() renders a single product or shows an error."""

    def test_shows_existing_product(self, mock_db, mock_user):
        from handlers.structures import Product

        p = Product(id=42, sku="SKU-X", name="Тестовый", price="5.00", category_id=1)

        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = p

        with patch("db.get_conn", return_value=mock_db):
            from handlers import products  # noqa: F811

            with patch("handlers.products.console") as mock_console:
                with patch(
                    "handlers.products.get_category_name_by_id", return_value="Кат"
                ):
                    products.show_product("42")
                    assert mock_console.print.call_count >= 1

    def test_renders_error_for_missing_product(self, mock_db, mock_user):
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = None

        with patch("db.get_conn", return_value=mock_db):
            from handlers import products  # noqa: F811

            with patch("handlers.products.render_error") as mock_error:
                products.show_product("999")
                mock_error.assert_called_once()
                assert "не найден" in mock_error.call_args[0][0]


class TestDeleteProductFKProtection:
    """delete_product() catches Exception on FK violation and renders an error."""

    def test_renders_error_on_fk_violation(self, mock_db, mock_user):
        from handlers.structures import Product

        p = Product(id=1, sku="DEL", name="Удаляемый", price="1.00", category_id=1)

        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = p

        # conn.execute() raises Exception to simulate FK violation
        mock_db.execute.side_effect = Exception("foreign key violation")

        with patch("db.get_conn", return_value=mock_db):
            from handlers import products  # noqa: F811

            with patch("handlers.products.render_error") as mock_error:
                with patch("handlers.products.prompt", return_value="y"):
                    with patch("handlers.products.console") as mock_console:
                        products.delete_product("1")
                        mock_error.assert_called_once()
                        assert "не может быть удалён" in mock_error.call_args[0][0]
