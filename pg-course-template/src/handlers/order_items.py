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
from products import get_product_name_by_id, get_products, get_product_by_id, get_product_by_sku
from structures import OrderItem, Order, Product
from validators import YesNoValidator, ChoiceValidator, QuantityValidator


def get_order_by_id(_id: int) -> Order | None:
    conn = get_conn()
    with conn.cursor(row_factory=class_row(Order)) as cur:
        cur.execute("SELECT * FROM sales.orders WHERE id = %s", (_id,))
        order: Order | None = cur.fetchone()

    return order


def check_order(order_id: int) -> bool:
    order = get_order_by_id(order_id)
    if order is None:
        render_error(f"Нет заказа с ID {order_id}")
        return False
    if order.status != "unpublished":
        render_error(f"Заказ с ID {order_id} уже опубликован и не может быть изменён")
        return False

    return True


def get_sku(product_name_with_sku: str) -> str | None:
    start = product_name_with_sku.find("(")
    end = product_name_with_sku.find(")", start)
    if start != -1 and end != -1:
        return product_name_with_sku[start + 1:end]
    return None


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


@command("add order_item", "добавить товар к заказу (интерактивно)", CATEGORY_ORDER_ITEMS)
def add_order_item(order_id: int) -> None:
    conn = get_conn()

    if not check_order(order_id):
        return

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

    # TODO здесь бы на самом деле лучше подошел choice
    product_name_with_sku = prompt(
        "Имя товара: ",
        validator=product_name_validator,
        completer=product_name_completer
    ).strip()
    sku = get_sku(product_name_with_sku)
    product: Product = get_product_by_sku(sku)

    with conn.cursor(row_factory=class_row(OrderItem)) as cur:
        cur.execute("SELECT * FROM sales.order_items WHERE order_id = %s AND product_id=%s",
                    (order_id, product.id))
        item: OrderItem | None = cur.fetchone()

    if not item is None:
        render_error(
            f"В заказе с ID {order_id} уже есть такой товар,"
            f" если желаете изменить количество - воспользуйтесь командой 'edit order_item'")
        return

    quantity = prompt("Количество: ", validator=QuantityValidator()).strip()

    with conn.transaction():
        with conn.cursor(row_factory=class_row(OrderItem)) as cur:
            item: OrderItem = cur.execute(
                """INSERT INTO sales.order_items (order_id, product_id, quantity, price) 
                VALUES (%s, %s, %s, %s) RETURNING *""",
                (order_id, product.id, quantity, product.price),
            ).fetchone()

        order: Order = get_order_by_id(order_id)
        total_amount = order.total_amount + item.quantity * item.price
        conn.execute(
            "UPDATE sales.orders SET total_amount = %s WHERE id = %s",
            (total_amount, order_id),
        )

    console.print(f"[green]Товар {product.name} добавлен к заказу ({order_id})  [/green]")

    answer = prompt("Желаете добавить еще товары? (y/n, д/н): ", validator=YesNoValidator())
    if YesNoValidator.is_yes(answer):
        add_order_item(order_id)


@command("edit order_item", "редактировать товар в заказе", CATEGORY_ORDER_ITEMS)
def edit_order_item(order_id: int) -> None:
    conn = get_conn()

    if not check_order(order_id):
        return

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

    with conn.transaction():
        conn.execute(
            """UPDATE sales.order_items SET quantity = %s, price = %s
            WHERE order_id = %s AND product_id=%s""",
            (quantity, product.price, order_id, product_id)
        )
        order = get_order_by_id(order_id)
        total_amount = (order.total_amount -
                        Decimal(item.quantity) * item.price +
                        Decimal(quantity) * product.price)
        conn.execute(
            "UPDATE sales.orders SET total_amount = %s WHERE id = %s",
            (total_amount, order_id),
        )

    console.print(f"[green]Товар {product.name} обновлен в заказе ({order_id})  [/green]")


@command("delete order_item", "удалить товар из заказа", CATEGORY_ORDER_ITEMS)
def delete_order_item(order_id: int) -> None:
    conn = get_conn()

    if not check_order(order_id):
        return

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
        with conn.transaction():
            conn.execute("DELETE FROM sales.order_items WHERE order_id = %s AND product_id=%s",
                         (order_id, product_id))
            order = get_order_by_id(order_id)
            total_amount = order.total_amount - Decimal(item.quantity) * item.price
            conn.execute(
                "UPDATE sales.orders SET total_amount = %s WHERE id = %s",
                (total_amount, order_id),
            )

        console.print(f"[green]Товар удален из заказа ({order_id}) [/green]")
