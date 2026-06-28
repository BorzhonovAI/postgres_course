"""Unit tests for product category handlers (handlers/product_categories.py).

Covers helper functions (product_categories_count, products_count_by_category_id,
get_category_name_by_id, get_category_by_name) and commands (show_category,
delete_all_product_categories with FK-safe truncate order).
"""

from unittest.mock import MagicMock, patch

import pytest


class TestProductCategoriesCount:
    """product_categories_count() returns the row count from catalog.product_categories."""

    def test_returns_integer_count(self, mock_db, mock_user):
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = (3,)

        with patch("db.get_conn", return_value=mock_db):
            from handlers import product_categories  # noqa: F811

            count = product_categories.product_categories_count()
            assert count == 3


class TestProductsCountByCategoryId:
    """products_count_by_category_id() counts products belonging to a category."""

    def test_returns_count_for_existing_category(self, mock_db, mock_user):
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = (7,)

        with patch("db.get_conn", return_value=mock_db):
            from handlers import product_categories  # noqa: F811

            count = product_categories.products_count_by_category_id(1)
            assert count == 7

    def test_returns_zero_for_empty_category(self, mock_db, mock_user):
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = (0,)

        with patch("db.get_conn", return_value=mock_db):
            from handlers import product_categories  # noqa: F811

            count = product_categories.products_count_by_category_id(999)
            assert count == 0


class TestGetCategoryByName:
    """get_category_by_name() looks up a category by name."""

    def test_finds_existing_category(self, mock_db, mock_user):
        from handlers.structures import ProductCategory

        cat = ProductCategory(id=2, name="Периферия")

        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = cat

        with patch("db.get_conn", return_value=mock_db):
            from handlers import product_categories  # noqa: F811

            result = product_categories.get_category_by_name("Периферия")
            assert result is not None
            assert result.id == 2
            assert result.name == "Периферия"

    def test_returns_none_for_unknown_name(self, mock_db, mock_user):
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = None

        with patch("db.get_conn", return_value=mock_db):
            from handlers import product_categories  # noqa: F811

            result = product_categories.get_category_by_name("Неизвестная")
            assert result is None


class TestGetCategoryNameById:
    """get_category_name_by_id() maps a category ID to its name."""

    def test_returns_name_for_existing_id(self, mock_db, mock_user):
        from handlers.structures import ProductCategory

        cat = ProductCategory(id=5, name="Комплектующие")

        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = cat

        with patch("db.get_conn", return_value=mock_db):
            from handlers import product_categories  # noqa: F811

            name = product_categories.get_category_name_by_id(5)
            assert name == "Комплектующие"

    def test_returns_none_for_unknown_id(self, mock_db, mock_user):
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = None

        with patch("db.get_conn", return_value=mock_db):
            from handlers import product_categories  # noqa: F811

            name = product_categories.get_category_name_by_id(999)
            assert name is None


class TestShowCategory:
    """show_category() renders a single category or shows an error."""

    def test_shows_existing_category(self, mock_db, mock_user):
        from handlers.structures import ProductCategory

        cat = ProductCategory(id=3, name="Сетевое оборудование")

        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = cat

        with patch("db.get_conn", return_value=mock_db):
            from handlers import product_categories  # noqa: F811

            with patch("handlers.product_categories.console") as mock_console:
                product_categories.show_category("3")
                assert mock_console.print.call_count >= 1

    def test_renders_error_for_missing_category(self, mock_db, mock_user):
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = None

        with patch("db.get_conn", return_value=mock_db):
            from handlers import product_categories  # noqa: F811

            with patch("handlers.product_categories.render_error") as mock_error:
                product_categories.show_category("999")
                mock_error.assert_called_once()
                assert "не найдена" in mock_error.call_args[0][0]


class TestDeleteAllProductCategories:
    """delete_all_product_categories() truncates products before categories (FK safety)."""

    def test_truncate_order_products_then_categories(self, mock_db, mock_user):
        # Simulate count of existing categories
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = (5,)

        with patch("db.get_conn", return_value=mock_db):
            from handlers import product_categories  # noqa: F811

            with patch("handlers.product_categories.prompt", return_value="y"):
                with patch("handlers.product_categories.console") as mock_console:
                    # Mock transaction context manager
                    mock_tx = MagicMock()
                    mock_tx.__enter__ = MagicMock(return_value=None)
                    mock_tx.__exit__ = MagicMock(return_value=False)
                    mock_db.transaction = MagicMock(return_value=mock_tx)

                    product_categories.delete_all_product_categories()

                    # Verify execute calls inside transaction:
                    # products truncated BEFORE categories (FK constraint)
                    calls = [c[0][0] for c in mock_db.execute.call_args_list]
                    products_call = [c for c in calls if "catalog.products" in c]
                    categories_call = [
                        c for c in calls if "catalog.product_categories" in c
                    ]

                    assert len(products_call) >= 1, "TRUNCATE products was not called"
                    assert (
                        len(categories_call) >= 1
                    ), "TRUNCATE categories was not called"

                    # Products must be truncated before categories
                    products_index = calls.index(products_call[0])
                    categories_index = calls.index(categories_call[0])
                    assert (
                        products_index < categories_index
                    ), "Products should be truncated before categories (FK safety)"
