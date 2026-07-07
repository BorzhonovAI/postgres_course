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

    # Таблица запасов
    with conn.cursor() as cur:
        cur.execute(
            """SELECT p.name, p.sku, s.quantity
               FROM inventory.stock s
               JOIN catalog.products p ON s.product_id = p.id
               WHERE s.warehouse_id = %s
               ORDER BY p.name""",
            (warehouse_id,),
        )
        stocks = cur.fetchall()

    if not stocks:
        render_error(f"На складе #{warehouse_id} нет запасов")
        return

    table = Table(
        title=f"Запасы на складе #{warehouse_id}",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Товар", style="yellow", min_width=25)
    table.add_column("Остаток", style="red", min_width=10, justify="right")

    for product_name, sku, quantity in stocks:
        table.add_row(f"{product_name} ({sku})", str(quantity))

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

    # Таблица остатков по складам
    with conn.cursor() as cur:
        cur.execute(
            """SELECT w.city_id, w.address, s.quantity
               FROM inventory.stock s
               JOIN catalog.products p ON s.product_id = p.id
               JOIN catalog.warehouses w ON s.warehouse_id = w.id
               WHERE p.sku = %s
               ORDER BY w.city_id""",
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
    table.add_column("Остаток", style="red", min_width=10, justify="right")

    for city_id, address, quantity in stocks:
        full_address = f"г. {get_city_name(city_id)}, {address}"
        table.add_row(
            full_address,
            str(quantity),
        )

    console.print(table)
