from prompt_toolkit import prompt
from prompt_toolkit.shortcuts import choice
from psycopg.rows import class_row
from rich.panel import Panel
from rich.table import Table

from commands import command, CATEGORY_ORDERS
from console import console, render_error
from db import get_conn
from order_items import add_order_item
from structures import Order
from validators import YesNoValidator
from warehouses import get_warehouse_full_address, get_warehouses


def _render_order(order: Order):
    table = Table(show_header=False, box=None, padding=(0, 2))

    table.add_column("Поле", style="bold cyan", width=15)
    table.add_column("Значение", style="white")

    table.add_row("ID", str(order.id))
    table.add_row("Статус", order.status)
    table.add_row("Суммарная стоимость", str(order.total_amount))
    table.add_row("Время создания", order.created_at)
    address = get_warehouse_full_address(order.warehouse_id)
    table.add_row("Склад", address if len(address) != 0 else "Неизвестно")

    panel = Panel(
        table,
        expand=False,
        title=f"[bold green]Заказ #{order.id}[/bold green]",
        border_style="green",
    )

    console.print(panel)


@command("list orders", "список всех заказов", CATEGORY_ORDERS)
def list_orders() -> None:
    conn = get_conn()
    table = Table(title="Заказы", show_header=True, header_style="bold cyan")

    table.add_column("ID", style="dim", width=6, justify="right")
    table.add_column("Статус", style="green", min_width=20)
    table.add_column("Суммарная стоимость", style="yellow", min_width=30)
    table.add_column("Время создания", style="magenta", min_width=15)
    table.add_column("Склад", style="red", min_width=15)

    with conn.cursor(row_factory=class_row(Order)) as cur:
        cur.execute("SELECT * FROM sales.orders")
        orders: list[Order] = cur.fetchall()

    for order in orders:
        address = get_warehouse_full_address(order.warehouse_id)
        table.add_row(
            str(order.id),
            order.status,
            str(order.total_amount),
            order.created_at,
            address if len(address) != 0 else "Неизвестно",
        )
    console.print(table)


@command("show order", "информация о заказе", CATEGORY_ORDERS)
def show_order(_id: str) -> None:
    conn = get_conn()
    with conn.cursor(row_factory=class_row(Order)) as cur:
        cur.execute("SELECT * FROM sales.orders WHERE id = %s", (_id,))
        order: Order | None = cur.fetchone()

    if order is None:
        render_error(f"Заказ с ID {_id} не найден")
        return

    _render_order(order)


@command("add order", "добавить заказ (интерактивно)", CATEGORY_ORDERS)
def add_order() -> None:
    conn = get_conn()

    warehouses = get_warehouses()
    warehouses_options = [(w.id, f"г. {w.city}, {w.address}") for w in warehouses]

    warehouse_id = choice(
        message="Выберите склад:",
        options=warehouses_options
    )

    order_id = conn.execute(
        "INSERT INTO sales.orders (warehouse_id) VALUES (%s) RETURNING id",
        (warehouse_id,),
    ).fetchone()[0]

    answer = prompt("Желаете добавить товары к заказу? (y/n, д/н): ", validator=YesNoValidator())
    if YesNoValidator.is_yes(answer):
        add_order_item(order_id)

    console.print(f"[green]Заказ #{order_id} добавлен [/green]")
    show_order(order_id)


@command("edit order", "редактировать заказ", CATEGORY_ORDERS)
def edit_order(_id: str) -> None:
    conn = get_conn()

    with conn.cursor(row_factory=class_row(Order)) as cur:
        cur.execute("SELECT * FROM sales.orders WHERE id = %s", (_id,))
        order: Order | None = cur.fetchone()

    if order is None:
        render_error(f"Заказ с ID {_id} не найден")
        return

    if order.status != "unpublished":
        render_error(f"Заказ с ID {_id} опубликован и не может быть отредактирован")
        return

    warehouses = get_warehouses()
    warehouses_options = [(w.id, f"г. {w.city}, {w.address}") for w in warehouses]

    warehouse_id = choice(
        message="Выберите склад:",
        options=warehouses_options,
        default=order.warehouse_id
    )

    # TODO можно добавить вызов edit_order_item

    conn.execute(
        "UPDATE sales.orders SET warehouse_id = %s WHERE id = %s",
        (warehouse_id, _id),
    )

    console.print(f"[green]Заказ #{_id} обновлен [/green]")


@command("delete order", "удалить заказ", CATEGORY_ORDERS)
def delete_order(_id: str) -> None:
    conn = get_conn()
    with conn.cursor(row_factory=class_row(Order)) as cur:
        cur.execute("SELECT * FROM sales.orders WHERE id = %s", (_id,))
        order: Order | None = cur.fetchone()

    if order is None:
        render_error(f"Заказ с ID {_id} не найден")
        return

    _render_order(order)

    answer = prompt("Вы уверены? (y/n, д/н): ", validator=YesNoValidator())

    if YesNoValidator.is_yes(answer):
        conn.execute("DELETE FROM sales.orders WHERE id = %s", (_id,))
        conn.execute("DELETE FROM sales.order_items WHERE order__id = %s", (_id,))
        console.print(f"[green]Заказ #{_id} удален [/green]")


@command("publish order", "опубликовать заказ", CATEGORY_ORDERS)
def publish_order(_id: str) -> None:
    conn = get_conn()

    with conn.cursor(row_factory=class_row(Order)) as cur:
        cur.execute("SELECT * FROM sales.orders WHERE id = %s", (_id,))
        order: Order | None = cur.fetchone()

    if order is None:
        render_error(f"Заказ с ID {_id} не найден")
        return

    if order.status != "unpublished":
        render_error(f"Заказ с ID {_id}  уже опубликован")
        return

    conn.execute(
        "UPDATE sales.orders SET status = %s WHERE id = %s",
        ("new", _id),
    )

    console.print(f"[green]Заказ #{_id} опубликован [/green]")
