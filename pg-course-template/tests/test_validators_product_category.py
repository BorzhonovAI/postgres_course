"""Unit tests for ProductCategoryValidator (validators.py).

ProductCategoryValidator is tested separately from other validators
because it requires a database connection (queries catalog.product_categories)
and lazily imports handler modules.
"""

import sys
from unittest.mock import MagicMock, patch

from prompt_toolkit.validation import ValidationError
import pytest


class TestProductCategoryValidator:
    """ProductCategoryValidator validates category names against the database."""

    def _mock_product_categories_module(self):
        """Create a fake product_categories module for the lazy import."""
        from handlers.structures import ProductCategory

        fake_mod = MagicMock()
        fake_mod.ProductCategory = ProductCategory
        return fake_mod

    def test_accepts_existing_category(self, mock_db, mock_user, document):
        """Valid category name passes validation."""
        mock_cursor = mock_db.cursor.return_value
        mock_cat = MagicMock(id=1, name="Электроника")
        mock_cursor.fetchone.return_value = mock_cat

        fake_mod = self._mock_product_categories_module()

        with patch("db.get_conn", return_value=mock_db):
            with patch.dict(sys.modules, {"product_categories": fake_mod}):
                from validators import ProductCategoryValidator

                validator = ProductCategoryValidator()
                # No exception means success
                validator.validate(document("Электроника"))

    def test_rejects_non_existent_category(self, mock_db, mock_user, document):
        """Category name not in DB raises ValidationError."""
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchone.return_value = None

        fake_mod = self._mock_product_categories_module()

        with patch("db.get_conn", return_value=mock_db):
            with patch.dict(sys.modules, {"product_categories": fake_mod}):
                from validators import ProductCategoryValidator

                validator = ProductCategoryValidator()
                with pytest.raises(ValidationError) as exc:
                    validator.validate(document("Неизвестная"))
                assert "не найдена" in exc.value.message
                # Error cursor position should be at the end of the text
                assert exc.value.cursor_position == len("Неизвестная")

    def test_rejects_empty_input(self, mock_db, mock_user, document):
        """Empty string raises ValidationError."""
        fake_mod = self._mock_product_categories_module()

        with patch("db.get_conn", return_value=mock_db):
            with patch.dict(sys.modules, {"product_categories": fake_mod}):
                from validators import ProductCategoryValidator

                validator = ProductCategoryValidator()
                with pytest.raises(ValidationError) as exc:
                    validator.validate(document(""))
                assert "не может быть пустым" in exc.value.message
                assert exc.value.cursor_position == 0

    def test_rejects_whitespace_only(self, mock_db, mock_user, document):
        """Whitespace-only string is treated as empty."""
        fake_mod = self._mock_product_categories_module()

        with patch("db.get_conn", return_value=mock_db):
            with patch.dict(sys.modules, {"product_categories": fake_mod}):
                from validators import ProductCategoryValidator

                validator = ProductCategoryValidator()
                with pytest.raises(ValidationError) as exc:
                    validator.validate(document("   "))
                assert "не может быть пустым" in exc.value.message

    def test_queries_with_correct_name(self, mock_db, mock_user, document):
        """Validator queries the database with the provided text."""
        mock_cursor = mock_db.cursor.return_value
        mock_cat = MagicMock(id=2, name="Канцелярия")
        mock_cursor.fetchone.return_value = mock_cat

        fake_mod = self._mock_product_categories_module()

        with patch("db.get_conn", return_value=mock_db):
            with patch.dict(sys.modules, {"product_categories": fake_mod}):
                from validators import ProductCategoryValidator

                validator = ProductCategoryValidator()
                validator.validate(document("Канцелярия"))
                # Verify the query used the correct parameter
                mock_cursor.execute.assert_called()
                call_args = mock_cursor.execute.call_args
                assert call_args[0][1] == ("Канцелярия",)  # positional params
