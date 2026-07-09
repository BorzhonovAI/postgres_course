from prompt_toolkit import prompt
from prompt_toolkit.shortcuts import choice
from psycopg.rows import class_row
from rich.panel import Panel
from rich.table import Table

from auth import ROLE_SALES_MANAGER, ROLE_INVENTORY_MANAGER, auth_user
from commands import command, CATEGORY_ORDERS
from console import console, render_error
from db import get_conn
from .order_items import add_order_item
from .products import get_product_by_id
from .structures import Order, OrderItem
from users import get_user
from validators import YesNoValidator
from .warehouses import get_warehouse_full_address, get_warehouses, get_city_name


def _get_item_status(order: Order, item: OrderItem) -> str:
    """
    Вычисляемый статус позиции заказа.

    Логика:
    - order.status = 'new' → "ожидает обработки"
    - Есть запись в inventory.reserves → "в резерве"
    - Есть незавершённый transfer_item (shipped, not arrived/received) → "в пути" + детали
    - Есть запись в inventory.delivery_items → "запланирована отгрузка" / "отгружено"
    - order.status == 'processing' и ничего выше → "ожидает обработки"
    """
    conn = get_conn()

    # 1. Заказ ещё не в работе
    if order.status == "new":
        return "ожидает обработки"

    with conn.cursor() as cur:
        # 2. Проверяем резерв (нужное количество)
        cur.execute(
            """SELECT quantity FROM inventory.reserves
               WHERE order_id = %s AND product_id = %s
               AND quantity >= %s""",
            (order.id, item.product_id, item.quantity),
        )
        if cur.fetchone() is not None:
            return "в резерве"

        # 3. Проверяем трансферы (перемещение из другого склада)
        cur.execute(
            """SELECT t.id, t.from_warehouse_id, t.status, t.arriving_at
               FROM inventory.transfer_items ti
               JOIN inventory.transfers t ON ti.transfer_id = t.id
               WHERE ti.product_id = %s
                 AND t.to_warehouse_id = %s
                 AND ti.status = 'shipped'
                 AND t.status IN ('shipping', 'in_transit')
               ORDER BY t.created_at DESC
               LIMIT 1""",
            (item.product_id, order.warehouse_id),
        )
        transfer = cur.fetchone()
        if transfer is not None:
            transfer_id, from_warehouse_id, transfer_status, arriving_at = transfer
            if arriving_at is not None:
                return (
                    f"в пути (из склада #{from_warehouse_id}), "
                    f"ожидаемая доставка {arriving_at.astimezone().strftime('%d.%m.%Y %H:%M')}"
                )
            return f"в пути (из склада #{from_warehouse_id})"

        # 4. Проверяем накладную доставки
        cur.execute(
            """SELECT status FROM inventory.delivery_items
               WHERE order_id = %s AND product_id = %s""",
            (order.id, item.product_id),
        )
        delivery_item = cur.fetchone()
        if delivery_item is not None:
            if delivery_item[0] == "shipped":
                return "отгружено"
            return "запланирована отгрузка"

        # 5. Заказ в обработке, но ничего не произошло
        if order.status == "processing":
            return "ожидает обработки"

        return "ожидает обработки"


def _render_order(order: Order):
    table = Table(show_header=False, box=None, padding=(0, 2))

    table.add_column("Поле", style="bold cyan", width=20)
    table.add_column("Значение", style="white")

    table.add_row("ID", str(order.id))
    table.add_row("Статус", order.status)
    table.add_row("Суммарная стоимость", str(order.total_amount))
    table.add_row(
        "Время создания", order.created_at.astimezone().isoformat(timespec="seconds")
    )
    address = get_warehouse_full_address(order.warehouse_id)
    table.add_row("Склад", address if len(address) != 0 else "Неизвестно")
    user = get_user(order.created_by_id)
    table.add_row("Владелец", user.username)
    if order.processing_by is not None:
        proc_user = get_user(order.processing_by)
        table.add_row("Обработчик", proc_user.username if proc_user else "Неизвестно")

    panel = Panel(
        table,
        expand=False,
        title=f"[bold green]Заказ #{order.id}[/bold green]",
        border_style="green",
    )

    console.print(panel)


@command("list orders", "список всех заказов", CATEGORY_ORDERS, [ROLE_SALES_MANAGER])
def list_orders() -> None:
    conn = get_conn()
    table = Table(title="Заказы", show_header=True, header_style="bold cyan")

    table.add_column("ID", style="dim", width=6, justify="right")
    table.add_column("Статус", style="green", min_width=20)
    table.add_column("Суммарная стоимость", style="yellow", min_width=30)
    table.add_column("Время создания", style="magenta", min_width=15)
    table.add_column("Склад", style="red", min_width=15)
    table.add_column("Владелец", style="magenta", min_width=15)

    with conn.cursor(row_factory=class_row(Order)) as cur:
        cur.execute("SELECT * FROM sales.orders")
        orders: list[Order] = cur.fetchall()

    for order in orders:
        address = get_warehouse_full_address(order.warehouse_id)
        user = get_user(order.created_by_id)
        table.add_row(
            str(order.id),
            order.status,
            str(order.total_amount),
            order.created_at.astimezone().isoformat(timespec="seconds"),
            address if len(address) != 0 else "Неизвестно",
            user.username,
        )
    console.print(table)


@command(
    "list orders new",
    "список заказов со статусом new",
    CATEGORY_ORDERS,
    [ROLE_INVENTORY_MANAGER],
)
def list_orders_new() -> None:
    conn = get_conn()
    table = Table(title="Заказы — new", show_header=True, header_style="bold cyan")

    table.add_column("ID", style="dim", width=6, justify="right")
    table.add_column("Статус", style="green", min_width=20)
    table.add_column("Суммарная стоимость", style="yellow", min_width=30)
    table.add_column("Дата создания", style="magenta", min_width=18)
    table.add_column("Склад отгрузки", style="red", min_width=30)
    table.add_column("Владелец", style="cyan", min_width=15)

    with conn.cursor(row_factory=class_row(Order)) as cur:
        cur.execute("SELECT * FROM sales.orders WHERE status = 'new'")
        orders: list[Order] = cur.fetchall()

    if not orders:
        console.print("[yellow]Нет заказов со статусом new[/yellow]")
        return

    for order in orders:
        address = get_warehouse_full_address(order.warehouse_id)
        user = get_user(order.created_by_id)
        table.add_row(
            str(order.id),
            order.status,
            str(order.total_amount),
            order.created_at.astimezone().isoformat(timespec="seconds"),
            address if len(address) != 0 else "Неизвестно",
            user.username,
        )
    console.print(table)


@command(
    "list orders processing",
    "список заказов в обработке",
    CATEGORY_ORDERS,
    [ROLE_INVENTORY_MANAGER],
)
def list_orders_processing() -> None:
    conn = get_conn()
    table = Table(
        title="Заказы — в обработке", show_header=True, header_style="bold cyan"
    )

    table.add_column("ID", style="dim", width=6, justify="right")
    table.add_column("Статус", style="green", min_width=20)
    table.add_column("Суммарная стоимость", style="yellow", min_width=30)
    table.add_column("Дата создания", style="magenta", min_width=18)
    table.add_column("Склад отгрузки", style="red", min_width=30)
    table.add_column("Владелец", style="cyan", min_width=15)
    table.add_column("Обработчик", style="yellow", min_width=15)

    with conn.cursor(row_factory=class_row(Order)) as cur:
        cur.execute("SELECT * FROM sales.orders WHERE status = 'processing'")
        orders: list[Order] = cur.fetchall()

    if not orders:
        console.print("[yellow]Нет заказов в обработке[/yellow]")
        return

    for order in orders:
        address = get_warehouse_full_address(order.warehouse_id)
        user = get_user(order.created_by_id)
        proc_user = get_user(order.processing_by) if order.processing_by else None
        table.add_row(
            str(order.id),
            order.status,
            str(order.total_amount),
            order.created_at.astimezone().isoformat(timespec="seconds"),
            address if len(address) != 0 else "Неизвестно",
            user.username,
            proc_user.username if proc_user else "—",
        )
    console.print(table)


@command(
    "list orders my",
    "мои заказы (в обработке у текущего пользователя)",
    CATEGORY_ORDERS,
    [ROLE_INVENTORY_MANAGER],
)
def list_orders_my() -> None:
    conn = get_conn()
    table = Table(title="Мои заказы", show_header=True, header_style="bold cyan")

    table.add_column("ID", style="dim", width=6, justify="right")
    table.add_column("Статус", style="green", min_width=20)
    table.add_column("Суммарная стоимость", style="yellow", min_width=30)
    table.add_column("Дата создания", style="magenta", min_width=18)
    table.add_column("Склад отгрузки", style="red", min_width=30)
    table.add_column("Владелец", style="cyan", min_width=15)

    current_user = auth_user()
    with conn.cursor(row_factory=class_row(Order)) as cur:
        cur.execute(
            "SELECT * FROM sales.orders WHERE status = 'processing' AND processing_by = %s",
            (current_user.id,),
        )
        orders: list[Order] = cur.fetchall()

    if not orders:
        console.print("[yellow]У вас нет заказов в обработке[/yellow]")
        return

    for order in orders:
        address = get_warehouse_full_address(order.warehouse_id)
        user = get_user(order.created_by_id)
        table.add_row(
            str(order.id),
            order.status,
            str(order.total_amount),
            order.created_at.astimezone().isoformat(timespec="seconds"),
            address if len(address) != 0 else "Неизвестно",
            user.username,
        )
    console.print(table)


@command(
    "mark order processing",
    "взять заказ в обработку (new → processing)",
    CATEGORY_ORDERS,
    [ROLE_INVENTORY_MANAGER],
)
def mark_order_processing(_id: str) -> None:
    conn = get_conn()

    with conn.cursor(row_factory=class_row(Order)) as cur:
        cur.execute("SELECT * FROM sales.orders WHERE id = %s", (_id,))
        order: Order | None = cur.fetchone()

    if order is None:
        render_error(f"Заказ с ID {_id} не найден")
        return

    if order.status != "new":
        render_error(
            f"Заказ #{_id} имеет статус «{order.status}», а не «new». "
            "Только заказы со статусом new можно взять в обработку."
        )
        return

    _render_order(order)

    answer = prompt("Взять заказ в обработку? (y/n, д/н): ", validator=YesNoValidator())
    if not YesNoValidator.is_yes(answer):
        console.print("[yellow]Отменено[/yellow]")
        return

    current_user = auth_user()
    with conn.transaction():
        # re-check: заказ всё ещё new и его ещё никто не взял
        cur = conn.cursor()
        cur.execute(
            "SELECT status, processing_by FROM sales.orders WHERE id = %s FOR UPDATE",
            (_id,),
        )
        row = cur.fetchone()
        if row is None or row[0] != "new" or row[1] is not None:
            render_error(f"Заказ #{_id} уже в обработке, повторите попытку")
            return

        conn.execute(
            "UPDATE sales.orders SET status = 'processing', processing_by = %s WHERE id = %s",
            (current_user.id, _id),
        )

    console.print(f"[green]Заказ #{_id} взят в обработку[/green]")


@command(
    "show order",
    "информация о заказе",
    CATEGORY_ORDERS,
    [ROLE_SALES_MANAGER, ROLE_INVENTORY_MANAGER],
)
def show_order(_id: str) -> None:
    conn = get_conn()
    with conn.cursor(row_factory=class_row(Order)) as cur:
        cur.execute("SELECT * FROM sales.orders WHERE id = %s", (_id,))
        order: Order | None = cur.fetchone()

    if order is None:
        render_error(f"Заказ с ID {_id} не найден")
        return

    _render_order(order)

    # Таблица элементов заказа
    with conn.cursor(row_factory=class_row(OrderItem)) as cur:
        cur.execute(
            "SELECT * FROM sales.order_items WHERE order_id = %s",
            (_id,),
        )
        items: list[OrderItem] = cur.fetchall()

    if items:
        item_table = Table(
            title="Элементы заказа",
            show_header=True,
            header_style="bold cyan",
        )
        item_table.add_column("Товар", style="yellow", min_width=30)
        item_table.add_column("Цена", style="green", min_width=15, justify="right")
        item_table.add_column("Кол-во", style="red", min_width=10, justify="right")
        item_table.add_column("Статус", style="magenta", min_width=30)

        for it in items:
            product = get_product_by_id(it.product_id)
            name = (
                f"{product.name} ({product.sku})" if product else f"ID {it.product_id}"
            )
            status = _get_item_status(order, it)
            item_table.add_row(name, str(it.price), str(it.quantity), status)

        console.print(item_table)
    else:
        console.print("[dim]Нет элементов заказа[/dim]")


@command(
    "add order", "добавить заказ (интерактивно)", CATEGORY_ORDERS, [ROLE_SALES_MANAGER]
)
def add_order() -> None:
    conn = get_conn()

    warehouses = get_warehouses()
    warehouses_options = [
        (w.id, f"г. {get_city_name(w.city_id)}, {w.address}") for w in warehouses
    ]

    warehouse_id = choice(message="Выберите склад:", options=warehouses_options)

    user = auth_user()
    with conn.transaction():
        order_id = conn.execute(
            "INSERT INTO sales.orders (warehouse_id, created_by_id) VALUES (%s, %s) RETURNING id",
            (warehouse_id, user.id),
        ).fetchone()[0]

        answer = prompt(
            "Желаете добавить товары к заказу? (y/n, д/н): ", validator=YesNoValidator()
        )
        if YesNoValidator.is_yes(answer):
            add_order_item(order_id)

    console.print(f"[green]Заказ #{order_id} добавлен [/green]")
    show_order(order_id)


@command("edit order", "редактировать заказ", CATEGORY_ORDERS, [ROLE_SALES_MANAGER])
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
    warehouses_options = [
        (w.id, f"г. {get_city_name(w.city_id)}, {w.address}") for w in warehouses
    ]

    warehouse_id = choice(
        message="Выберите склад:",
        options=warehouses_options,
        default=order.warehouse_id,
    )

    conn.execute(
        "UPDATE sales.orders SET warehouse_id = %s WHERE id = %s",
        (warehouse_id, _id),
    )

    console.print(f"[green]Заказ #{_id} обновлен [/green]")


@command("delete order", "удалить заказ", CATEGORY_ORDERS, [ROLE_SALES_MANAGER])
def delete_order(_id: str) -> None:
    conn = get_conn()
    with conn.cursor(row_factory=class_row(Order)) as cur:
        cur.execute("SELECT * FROM sales.orders WHERE id = %s", (_id,))
        order: Order | None = cur.fetchone()

    if order is None:
        render_error(f"Заказ с ID {_id} не найден")
        return

    if order.status != "unpublished":
        render_error(f"Заказ с ID {_id} опубликован и не может быть удален")
        return

    _render_order(order)

    answer = prompt("Вы уверены? (y/n, д/н): ", validator=YesNoValidator())

    if YesNoValidator.is_yes(answer):
        conn.execute("DELETE FROM sales.orders WHERE id = %s", (_id,))

        console.print(f"[green]Заказ #{_id} удален [/green]")
    else:
        console.print("[yellow]Отменено[/yellow]")


@command("publish order", "опубликовать заказ", CATEGORY_ORDERS, [ROLE_SALES_MANAGER])
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
