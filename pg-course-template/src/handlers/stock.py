from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.shortcuts import choice
from rich.table import Table

from auth import ROLE_INVENTORY_MANAGER
from commands import command, CATEGORY_STOCK
from console import console, render_error
from db import get_conn
from .products import get_products
from .warehouses import get_city_name, get_warehouses
from validators import ChoiceValidator


@command(
    "view warehouse stock",
    "просмотр запасов на складе",
    CATEGORY_STOCK,
    [ROLE_INVENTORY_MANAGER],
)
def view_warehouse_stock() -> None:
    conn = get_conn()

    warehouses = get_warehouses()
    warehouses_options = [
        (w.id, f"г. {get_city_name(w.city_id)}, {w.address}") for w in warehouses
    ]

    warehouse_id = choice(message="Выберите склад:", options=warehouses_options)

    # Таблица запасов: сток, резерв, общее
    with conn.cursor() as cur:
        cur.execute(
            """WITH base AS (
                   SELECT p.name, p.sku,
                          COALESCE(SUM(s.quantity), 0) AS stock_qty,
                          COALESCE((
                              SELECT SUM(r.quantity)
                              FROM inventory.reserves r
                              WHERE r.product_id = p.id
                                AND r.order_id IN (
                                    SELECT o.id
                                    FROM sales.orders o
                                    WHERE o.status NOT IN ('shipped', 'new')
                                )
                          ), 0) AS reserve_qty
                     FROM catalog.products p
                     LEFT JOIN inventory.stock s ON s.product_id = p.id
                                                AND s.warehouse_id = %s
                    GROUP BY p.id, p.name, p.sku
               )
              SELECT name, sku, stock_qty, reserve_qty,
                     stock_qty + reserve_qty AS total_qty
                FROM base
               ORDER BY name""",
            (warehouse_id,),
        )
        stocks = cur.fetchall()

    if not stocks:
        render_error("В каталоге нет товаров")
        return

    table = Table(
        title=f"Запасы на складе #{warehouse_id}",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Товар", style="yellow", min_width=25)
    table.add_column("Сток", style="green", min_width=10, justify="right")
    table.add_column("Резерв", style="magenta", min_width=10, justify="right")
    table.add_column("Общее", style="red", min_width=10, justify="right")

    for product_name, sku, stock_qty, reserve_qty, total_qty in stocks:
        table.add_row(
            f"{product_name} ({sku})",
            str(stock_qty),
            str(reserve_qty),
            str(total_qty),
        )

    console.print(table)


@command(
    "view product stock",
    "просмотр остатков товара по всем складам",
    CATEGORY_STOCK,
    [ROLE_INVENTORY_MANAGER],
)
def view_product_stock() -> None:
    conn = get_conn()

    products = get_products()
    products_str = [f"{p.name} ({p.sku})" for p in products]
    product_completer = WordCompleter(products_str, ignore_case=True, sentence=True)
    product_validator = ChoiceValidator(
        products_str,
        message="Товар должен быть из списка. Используйте Tab для автодополнения.",
    )

    product_name_with_sku = prompt(
        "Имя товара: ",
        validator=product_validator,
        completer=product_completer,
    ).strip()

    # Извлекаем sku из строки "{name} ({sku})"
    sku = product_name_with_sku.split("(")[-1].rstrip(")")

    # Таблица остатков по складам: сток, резерв, общее
    with conn.cursor() as cur:
        cur.execute(
            """WITH base AS (
                   SELECT w.city_id, w.address,
                          COALESCE(SUM(s.quantity), 0) AS stock_qty,
                          COALESCE((
                              SELECT SUM(r.quantity)
                              FROM inventory.reserves r
                              WHERE r.product_id = p.id
                                AND r.order_id IN (
                                    SELECT o.id
                                    FROM sales.orders o
                                    WHERE o.status NOT IN ('shipped', 'new')
                                )
                          ), 0) AS reserve_qty
                     FROM inventory.stock s
                     JOIN catalog.products p ON s.product_id = p.id
                     JOIN catalog.warehouses w ON s.warehouse_id = w.id
                    WHERE p.sku = %s
                    GROUP BY w.id, w.city_id, w.address
               )
              SELECT city_id, address, stock_qty, reserve_qty,
                     stock_qty + reserve_qty AS total_qty
                FROM base
               ORDER BY stock_qty DESC""",
            (sku,),
        )
        stocks = cur.fetchall()

    if not stocks:
        render_error(f"Товар {product_name_with_sku} не найден")
        return

    table = Table(
        title=f"Остатки товара '{product_name_with_sku}'",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Склад", style="magenta", min_width=30)
    table.add_column("Сток", style="green", min_width=10, justify="right")
    table.add_column("Резерв", style="magenta", min_width=10, justify="right")
    table.add_column("Общее", style="red", min_width=10, justify="right")

    for city_id, address, stock_qty, reserve_qty, total_qty in stocks:
        full_address = f"г. {get_city_name(city_id)}, {address}"
        table.add_row(
            full_address,
            str(stock_qty),
            str(reserve_qty),
            str(total_qty),
        )

    console.print(table)
