from dataclasses import dataclass
from decimal import Decimal

from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.shortcuts import choice
from psycopg.rows import class_row
from rich.panel import Panel
from rich.table import Table

from commands import command, CATEGORY_ORDER_ITEMS
from console import console, render_error
from db import get_conn
from products import get_product_name_by_id, get_product_by_name, get_products, get_product_by_id
from validators import YesNoValidator, ChoiceValidator, QuantityValidator


@dataclass
class OrderItem:
    order_id: int
    product_id: int
    quantity: int
    price: Decimal


def _render_order_item(item: OrderItem) -> None:
    table = Table(show_header=False, box=None, padding=(0, 2))

    table.add_column("Поле", style="bold cyan", width=15)
    table.add_column("Значение", style="white")

    table.add_row("ID заказа", str(item.order_id))
    table.add_row("Имя товара", get_product_name_by_id(item.product_id))
    table.add_row("Количество", str(item.quantity))
    table.add_row("Цена за 1 шт.", str(item.price))

    panel = Panel(
        table,
        expand=False,
        title=f"[bold green]Элемент заказа #{item.product_id}[/bold green]",
        border_style="green",
    )

    console.print(panel)


@command("add order_item", "добавить товар(ы) к заказу (интерактивно)", CATEGORY_ORDER_ITEMS)
def add_order_item(order_id: str) -> None:
    conn = get_conn()

    # TODO check if order exists and its status

    products = get_products()

    if len(products) == 0:
        render_error(f"Нет товаров для добавления")
        return

    products_str = [f"{p.name} ({p.sku})" for p in products]
    product_name_completer = WordCompleter(products_str, ignore_case=True, sentence=True)
    product_name_validator = ChoiceValidator(
        products_str, message="Товар должен быть из списка. "
                              "Используйте Tab для автодополнения."
    )

    product_name = prompt(
        "Имя товара: ",
        validator=product_name_validator,
        completer=product_name_completer
    ).strip()
    product = get_product_by_name(product_name)
    with conn.cursor(row_factory=class_row(OrderItem)) as cur:
        cur.execute("SELECT * FROM sales.order_items WHERE order_id = %s AND product_id=%s",
                    (order_id, product.id))
        item: OrderItem | None = cur.fetchone()

    if item is None:
        render_error(
            f"В заказе с ID {order_id} уже есть такой товар,"
            f" если желаете изменить количество - воспользуйтесь командой 'edit order_item'")
        return

    quantity = prompt("Количество: ", validator=QuantityValidator()).strip()

    conn.execute(
        "INSERT INTO sales.order_items (order_id, product_id, quantity, price) VALUES (%s, %s, %s, %s)",
        (order_id, product.id, quantity, product.price),
    )

    console.print(f"[green]Товар(ы) {product.name} добавлен(ы) к заказу ({order_id})  [/green]")

    answer = prompt("Желаете добавить еще товары? (y/n, д/н): ", validator=YesNoValidator())
    if YesNoValidator.is_yes(answer):
        add_order_item(order_id)


@command("edit order_item", "редактировать товар(ы) в заказе", CATEGORY_ORDER_ITEMS)
def edit_order_item(order_id: str) -> None:
    conn = get_conn()

    # TODO check if order exists and its status

    with conn.cursor(row_factory=class_row(OrderItem)) as cur:
        cur.execute("SELECT * FROM sales.order_items WHERE order_id = %s", (order_id,))
        items: list[OrderItem] = cur.fetchall()

    if len(items) == 0:
        render_error(f"В заказе с ID {order_id} нет товаров")
        return

    products = [get_product_by_id(item.product_id) for item in items]
    products = filter(None, products)  # если товар был удален из таблицы с товарами
    products_options = [(p.id, f"{p.name} ({p.sku})") for p in products]

    product_id = choice(
        message="Выберите товар:",
        options=products_options
    )

    with conn.cursor(row_factory=class_row(OrderItem)) as cur:
        cur.execute("SELECT * FROM sales.order_items WHERE order_id = %s AND product_id=%s", (order_id, product_id))
        item: OrderItem = cur.fetchone()

    quantity = prompt("Количество: ", default=str(item.quantity), validator=QuantityValidator()).strip()
    product = get_product_by_id(product_id)

    conn.execute(
        """UPDATE sales.order_items SET quantity = %s, price = %s
        WHERE order_id = %s AND product_id=%s""",
        (quantity, product.price, order_id, product_id)
    )
    console.print(f"[green]Товар(ы) {product.name} обновлен(ы) в заказе ({order_id})  [/green]")


@command("delete order_item", "удалить товар(ы) из заказа", CATEGORY_ORDER_ITEMS)
def delete_order_item(order_id: str) -> None:
    conn = get_conn()

    # TODO check if order exists and its status

    with conn.cursor(row_factory=class_row(OrderItem)) as cur:
        cur.execute("SELECT * FROM sales.order_items WHERE order_id = %s", (order_id,))
        items: list[OrderItem] = cur.fetchall()

    if len(items) == 0:
        render_error(f"В заказе с ID {order_id} нет товаров")
        return

    products = [get_product_by_id(item.product_id) for item in items]
    products = filter(None, products)  # если товар был удален из таблицы с товарами
    products_options = [(p.id, f"{p.name} ({p.sku})") for p in products]

    product_id = choice(
        message="Выберите товар:",
        options=products_options
    )

    with conn.cursor(row_factory=class_row(OrderItem)) as cur:
        cur.execute("SELECT * FROM sales.order_items WHERE order_id = %s AND product_id=%s", (order_id, product_id))
        item: OrderItem = cur.fetchone()

    _render_order_item(item)

    answer = prompt("Вы уверены? (y/n, д/н): ", validator=YesNoValidator())

    if YesNoValidator.is_yes(answer):
        conn.execute("DELETE FROM sales.order_items WHERE order_id = %s AND product_id=%s", (order_id, product_id))
        console.print(f"[green]Товар(ы) удален(ы) из заказа ({order_id}) [/green]")
