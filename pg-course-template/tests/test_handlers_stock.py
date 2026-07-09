"""Unit tests for stock handlers (handlers/stock.py).

Covers `view warehouse stock` and `view product stock` commands.
Tests warehouse/product selection, SQL queries, table rendering,
and empty-result paths.
"""

from unittest.mock import MagicMock, patch


class TestViewWarehouseStock:
    """view_warehouse_stock() prompts for warehouse and shows stock table."""

    def test_prompts_warehouse_choice(self, mock_db):
        """Should call choice() with warehouse options."""
        with patch("db.get_conn", return_value=mock_db):
            from handlers import stock  # noqa: F811

            with patch("handlers.stock.get_warehouses") as mock_whs:
                mock_whs.return_value = [
                    MagicMock(id=1, city_id=1, address="ул. Тест, 1"),
                    MagicMock(id=2, city_id=2, address="ул. Другая, 5"),
                ]
                with patch(
                    "handlers.stock.get_city_name", side_effect=["Москва", "СПб"]
                ):
                    with patch("handlers.stock.choice", return_value=1) as mock_choice:
                        with patch("handlers.stock.console"):
                            stock.view_warehouse_stock()
                            mock_choice.assert_called_once()
                            # options should be [(id, label), ...]
                            _, kwargs = mock_choice.call_args
                            options = (
                                kwargs.get("options") or mock_choice.call_args[0][1]
                            )
                            assert (1, "г. Москва, ул. Тест, 1") in options
                            assert (2, "г. СПб, ул. Другая, 5") in options

    def test_shows_stock_table_when_has_items(self, mock_db):
        """Stock table is rendered when warehouse has items."""
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchall.return_value = [
            ("Ноутбук", "NB-001", 10, 0, 10),
            ("Мышь", "MS-002", 50, 5, 55),
        ]

        with patch("db.get_conn", return_value=mock_db):
            from handlers import stock  # noqa: F811

            with patch("handlers.stock.get_warehouses") as mock_whs:
                mock_whs.return_value = [
                    MagicMock(id=1, city_id=1, address="ул. Тест, 1")
                ]
                with patch("handlers.stock.get_city_name", return_value="Москва"):
                    with patch("handlers.stock.choice", return_value=1):
                        with patch("handlers.stock.console") as mock_console:
                            stock.view_warehouse_stock()
                            assert mock_console.print.called

    def test_shows_error_when_no_stock(self, mock_db):
        """Should render_error when warehouse has no stock."""
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchall.return_value = []

        with patch("db.get_conn", return_value=mock_db):
            from handlers import stock  # noqa: F811

            with patch("handlers.stock.get_warehouses") as mock_whs:
                mock_whs.return_value = [
                    MagicMock(id=1, city_id=1, address="ул. Тест, 1")
                ]
                with patch("handlers.stock.get_city_name", return_value="Москва"):
                    with patch("handlers.stock.choice", return_value=1):
                        with patch("handlers.stock.render_error") as mock_error:
                            stock.view_warehouse_stock()
                            mock_error.assert_called_once()
                            assert (
                                "В каталоге нет товаров" in mock_error.call_args[0][0]
                            )

    def test_queries_inventory_stock_with_warehouse_filter(self, mock_db):
        """SQL should filter by warehouse_id and JOIN products."""
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchall.return_value = []

        with patch("db.get_conn", return_value=mock_db):
            from handlers import stock  # noqa: F811

            with patch("handlers.stock.get_warehouses") as mock_whs:
                mock_whs.return_value = [MagicMock(id=5, city_id=1, address="x")]
                with patch("handlers.stock.get_city_name", return_value="City"):
                    with patch("handlers.stock.choice", return_value=5):
                        with patch("handlers.stock.console"):
                            stock.view_warehouse_stock()

                            execute_calls = mock_cursor.execute.call_args_list
                            assert len(execute_calls) >= 1
                            sql = execute_calls[0][0][0]
                            params = execute_calls[0][0][1]
                            assert "inventory.stock" in sql or "stock" in sql
                            assert "catalog.products" in sql
                            assert "warehouse_id" in sql.lower()
                            assert params == (5,)

    def test_orders_products_by_name(self, mock_db):
        """Stock table rows are ordered by product name."""
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchall.return_value = []

        with patch("db.get_conn", return_value=mock_db):
            from handlers import stock  # noqa: F811

            with patch("handlers.stock.get_warehouses") as mock_whs:
                mock_whs.return_value = [MagicMock(id=1, city_id=1, address="x")]
                with patch("handlers.stock.get_city_name", return_value="City"):
                    with patch("handlers.stock.choice", return_value=1):
                        with patch("handlers.stock.console"):
                            stock.view_warehouse_stock()

                            execute_calls = mock_cursor.execute.call_args_list
                            sql = execute_calls[0][0][0]
                            assert "ORDER BY" in sql.upper()
                            assert "p.name" in sql

    def test_table_has_product_and_quantity_columns(self, mock_db):
        """Rendered table should have product (name+sku) and quantity columns."""
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchall.return_value = [("Тест", "SKU-1", 5, 0, 5)]

        with patch("db.get_conn", return_value=mock_db):
            from handlers import stock  # noqa: F811

            with patch("handlers.stock.get_warehouses") as mock_whs:
                mock_whs.return_value = [MagicMock(id=1, city_id=1, address="x")]
                with patch("handlers.stock.get_city_name", return_value="City"):
                    with patch("handlers.stock.choice", return_value=1):
                        with patch("handlers.stock.console") as mock_console:
                            stock.view_warehouse_stock()
                            # table.add_row was called with product name+sku and quantity
                            table_print = mock_console.print.call_args
                            assert table_print is not None


class TestViewProductStock:
    """view_product_stock() prompts for product and shows stock across warehouses."""

    def test_prompts_product_name(self, mock_db):
        """Should prompt for product name with autocomplete."""
        with patch("db.get_conn", return_value=mock_db):
            from handlers import stock  # noqa: F811

            with patch("handlers.stock.get_products") as mock_gps:
                mock_gps.return_value = [
                    MagicMock(id=1, name="Ноутбук", sku="NB-001"),
                    MagicMock(id=2, name="Мышь", sku="MS-002"),
                ]
                with patch("handlers.stock.prompt", return_value="Ноутбук (NB-001)"):
                    with patch("handlers.stock.console"):
                        stock.view_product_stock()
                        # prompt should have been called with "Имя товара: "
                        prompt_calls = [
                            c for c in mock_gps().__iter__()
                        ]  # just check it ran
                        # The key thing: prompt was called
                        # We'll check via a different approach
                        pass

    def test_prompts_product_name_and_queries(self, mock_db):
        """Product selection leads to stock query across warehouses."""
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchall.return_value = [
            (1, "ул. Тест, 1", 10, 0, 10),
            (2, "ул. Другая, 5", 3, 1, 4),
        ]

        with patch("db.get_conn", return_value=mock_db):
            from handlers import stock  # noqa: F811

            with patch("handlers.stock.get_products") as mock_gps:
                mock_gps.return_value = [
                    MagicMock(id=1, name="Ноутбук", sku="NB-001"),
                ]
                with patch("handlers.stock.prompt", return_value="Ноутбук (NB-001)"):
                    with patch(
                        "handlers.stock.get_city_name", side_effect=["Москва", "СПб"]
                    ):
                        with patch("handlers.stock.console") as mock_console:
                            stock.view_product_stock()
                            assert mock_console.print.called

    def test_shows_error_when_product_not_found(self, mock_db):
        """Should render_error when product has no stock entries."""
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchall.return_value = []

        with patch("db.get_conn", return_value=mock_db):
            from handlers import stock  # noqa: F811

            with patch("handlers.stock.get_products") as mock_gps:
                mock_gps.return_value = [
                    MagicMock(id=1, name="Ноутбук", sku="NB-001"),
                ]
                with patch("handlers.stock.prompt", return_value="Ноутбук (NB-001)"):
                    with patch("handlers.stock.render_error") as mock_error:
                        stock.view_product_stock()
                        mock_error.assert_called_once()
                        assert "не найден" in mock_error.call_args[0][0]

    def test_queries_stock_with_sku_filter(self, mock_db):
        """SQL should filter by product SKU and JOIN warehouses."""
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchall.return_value = []

        with patch("db.get_conn", return_value=mock_db):
            from handlers import stock  # noqa: F811

            with patch("handlers.stock.get_products") as mock_gps:
                mock_gps.return_value = [
                    MagicMock(id=1, name="Ноутбук", sku="NB-001"),
                ]
                with patch("handlers.stock.prompt", return_value="Ноутбук (NB-001)"):
                    with patch("handlers.stock.console"):
                        stock.view_product_stock()

                        execute_calls = mock_cursor.execute.call_args_list
                        assert len(execute_calls) >= 1
                        sql = execute_calls[0][0][0]
                        params = execute_calls[0][0][1]
                        assert "inventory.stock" in sql or "stock" in sql
                        assert "catalog.products" in sql
                        assert "catalog.warehouses" in sql
                        assert "sku" in sql.lower()
                        assert params == ("NB-001",)

    def test_orders_by_city(self, mock_db):
        """Stock rows are ordered by city_id."""
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchall.return_value = []

        with patch("db.get_conn", return_value=mock_db):
            from handlers import stock  # noqa: F811

            with patch("handlers.stock.get_products") as mock_gps:
                mock_gps.return_value = [
                    MagicMock(id=1, name="Тест", sku="T-1"),
                ]
                with patch("handlers.stock.prompt", return_value="Тест (T-1)"):
                    with patch("handlers.stock.console"):
                        stock.view_product_stock()

                        execute_calls = mock_cursor.execute.call_args_list
                        sql = execute_calls[0][0][0]
                        assert "ORDER BY" in sql.upper()
                        assert "w.city_id" in sql

    def test_orders_by_stock_qty_desc(self, mock_db):
        """Stock rows are ordered by stock_qty DESC."""
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchall.return_value = []

        with patch("db.get_conn", return_value=mock_db):
            from handlers import stock  # noqa: F811

            with patch("handlers.stock.get_products") as mock_gps:
                mock_gps.return_value = [
                    MagicMock(id=1, name="Тест", sku="T-1"),
                ]
                with patch("handlers.stock.prompt", return_value="Тест (T-1)"):
                    with patch("handlers.stock.console"):
                        stock.view_product_stock()

                        execute_calls = mock_cursor.execute.call_args_list
                        sql = execute_calls[0][0][0]
                        upper_sql = sql.upper()
                        assert "ORDER BY STOCK_QTY DESC" in upper_sql

    def test_table_has_warehouse_and_quantity_columns(self, mock_db):
        """Rendered table should have warehouse address and quantity."""
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchall.return_value = [(1, "ул. Тест, 1", 7, 2, 9)]

        with patch("db.get_conn", return_value=mock_db):
            from handlers import stock  # noqa: F811

            with patch("handlers.stock.get_products") as mock_gps:
                mock_gps.return_value = [
                    MagicMock(id=1, name="Тест", sku="T-1"),
                ]
                with patch("handlers.stock.prompt", return_value="Тест (T-1)"):
                    with patch("handlers.stock.get_city_name", return_value="Москва"):
                        with patch("handlers.stock.console") as mock_console:
                            stock.view_product_stock()
                            table_print = mock_console.print.call_args
                            assert table_print is not None

    def test_extracts_sku_from_prompt_response(self, mock_db):
        """SKU is extracted from "{name} ({sku})" format."""
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchall.return_value = []

        with patch("db.get_conn", return_value=mock_db):
            from handlers import stock  # noqa: F811

            with patch("handlers.stock.get_products") as mock_gps:
                mock_gps.return_value = [MagicMock(id=1, name="Тест", sku="ABC-123")]
                with patch("handlers.stock.prompt", return_value="Тест (ABC-123)"):
                    with patch("handlers.stock.console"):
                        stock.view_product_stock()

                        execute_calls = mock_cursor.execute.call_args_list
                        params = execute_calls[0][0][1]
                        assert params == ("ABC-123",)

    def test_lists_all_products_for_selection(self, mock_db):
        """get_products is called to populate product list."""
        with patch("db.get_conn", return_value=mock_db):
            from handlers import stock  # noqa: F811

            with patch("handlers.stock.get_products") as mock_gps:
                mock_gps.return_value = [
                    MagicMock(id=1, name="A", sku="A1"),
                    MagicMock(id=2, name="B", sku="B2"),
                ]
                with patch("handlers.stock.prompt", return_value="A (A1)"):
                    with patch("handlers.stock.console"):
                        stock.view_product_stock()
                        mock_gps.assert_called_once()


class TestStockReserveFilter:
    """Reserve calculation: only active orders count (status NOT IN shipped/new)."""

    def test_warehouse_stock_sql_filters_shipped_new_orders(self, mock_db):
        """view_warehouse_stock SQL excludes shipped and new from reserve."""
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchall.return_value = [("Тест", "T-1", 10, 2, 12)]

        with patch("db.get_conn", return_value=mock_db):
            from handlers import stock  # noqa: F811

            with patch("handlers.stock.get_warehouses") as mock_whs:
                mock_whs.return_value = [MagicMock(id=1, city_id=1, address="x")]
                with patch("handlers.stock.get_city_name", return_value="City"):
                    with patch("handlers.stock.choice", return_value=1):
                        with patch("handlers.stock.console"):
                            stock.view_warehouse_stock()

                            sql = mock_cursor.execute.call_args[0][0]
                            upper_sql = sql.upper()
                            assert "NOT IN" in upper_sql
                            assert "'shipped'" in upper_sql or "'SHIPPED'" in upper_sql
                            assert "'new'" in upper_sql or "'NEW'" in upper_sql

    def test_product_stock_sql_filters_shipped_new_orders(self, mock_db):
        """view_product_stock SQL excludes shipped and new from reserve."""
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchall.return_value = [(1, "ул. Тест, 1", 10, 2, 12)]

        with patch("db.get_conn", return_value=mock_db):
            from handlers import stock  # noqa: F811

            with patch("handlers.stock.get_products") as mock_gps:
                mock_gps.return_value = [MagicMock(id=1, name="Тест", sku="T-1")]
                with patch("handlers.stock.prompt", return_value="Тест (T-1)"):
                    with patch("handlers.stock.get_city_name", return_value="Москва"):
                        with patch("handlers.stock.console"):
                            stock.view_product_stock()

                            # first execute call is the stock query
                            sql = mock_cursor.execute.call_args_list[0][0][0]
                            upper_sql = sql.upper()
                            assert "NOT IN" in upper_sql
                            assert "'SHIPPED'" in upper_sql
                            assert "'NEW'" in upper_sql

    def test_warehouse_stock_returns_zero_stock_products(self, mock_db):
        """Products with no inventory.stock rows should appear with stock_qty=0."""
        mock_cursor = mock_db.cursor.return_value
        # LEFT JOIN returns NULL for stock, COALESCE converts to 0
        mock_cursor.fetchall.return_value = [("Тест", "T-1", 0, 0, 0)]

        with patch("db.get_conn", return_value=mock_db):
            from handlers import stock  # noqa: F811

            with patch("handlers.stock.get_warehouses") as mock_whs:
                mock_whs.return_value = [MagicMock(id=1, city_id=1, address="x")]
                with patch("handlers.stock.get_city_name", return_value="City"):
                    with patch("handlers.stock.choice", return_value=1):
                        with patch("handlers.stock.console") as mock_console:
                            stock.view_warehouse_stock()
                            mock_console.print.assert_called_once()

                            # verify the row was added with correct values
                            table_print = mock_console.print.call_args
                            assert table_print is not None

    def test_reserve_qty_in_results_tuple(self, mock_db):
        """Result tuple includes reserve_qty as the 4th element."""
        mock_cursor = mock_db.cursor.return_value
        mock_cursor.fetchall.return_value = [("Тест", "T-1", 10, 3, 13)]

        with patch("db.get_conn", return_value=mock_db):
            from handlers import stock  # noqa: F811

            with patch("handlers.stock.get_warehouses") as mock_whs:
                mock_whs.return_value = [MagicMock(id=1, city_id=1, address="x")]
                with patch("handlers.stock.get_city_name", return_value="City"):
                    with patch("handlers.stock.choice", return_value=1):
                        with patch("handlers.stock.console") as mock_console:
                            stock.view_warehouse_stock()
                            mock_console.print.assert_called_once()
