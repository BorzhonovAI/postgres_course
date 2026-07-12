from datetime import datetime
from typing import Any

from prompt_toolkit import prompt
from prompt_toolkit.shortcuts import choice as prompt_choice
from psycopg.errors import UniqueViolation
from psycopg.rows import class_row, dict_row
from rich.table import Table

from auth import ROLE_INVENTORY_MANAGER, auth_user
from commands import command, CATEGORY_TRANSFERS
from console import console, render_error
from db import get_conn
from .structures import Transfer, TransferItem
from users import get_user
from validators import QuantityValidator, YesNoValidator
from .warehouses import get_warehouse_full_address, get_warehouses


def _get_route_pairs() -> dict[int, list[int]]:
    """Возвращает маппинг: from_warehouse_id -> [to_warehouse_ids].

    Для каждого склада, из которого есть хотя бы один маршрут,
    перечисляет склады, в которые из него можно добраться.
    """
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT w_from.id, w_to.id
              FROM catalog.warehouses w_from
              JOIN inventory.routes r ON r.from_city_id = w_from.city_id
              JOIN catalog.warehouses w_to ON w_to.city_id = r.to_city_id
            ORDER BY w_from.id, w_to.id
            """)
        rows = cur.fetchall()

    mapping: dict[int, list[int]] = {}
    for from_id, to_id in rows:
        mapping.setdefault(from_id, []).append(to_id)
    return mapping


def _render_transfer_items(transfer: Transfer, items: list[dict[str, Any]]) -> None:
    """Рендерит таблицу items для одного transfer."""
    table = Table(
        title=f"Позиции трансфера #{transfer.id}",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("ID", style="dim", width=6, justify="right")
    table.add_column("Товар", style="yellow", min_width=35)
    table.add_column("Количество", style="green", min_width=10, justify="right")
    table.add_column("Заказ", style="magenta", min_width=10, justify="right")
    table.add_column("Добавил", style="cyan", min_width=20)
    table.add_column("Статус", style="dim", min_width=15)

    for item in items:
        user = get_user(item["requested_by"])
        username = user.username if user else "Неизвестно"

        product_display = (
            f"ID {item['product_id']} — {item['product_name']}"
            if item["product_name"]
            else f"ID {item['product_id']}"
        )

        order_id = item["order_id"]
        order_display = str(order_id) if order_id else "—"

        table.add_row(
            str(item["id"]),
            product_display,
            str(item["quantity"]),
            order_display,
            username,
            item["status"],
        )

    console.print(table)


@command(
    "list transfers planned all",
    "список всех запланированных перемещений",
    CATEGORY_TRANSFERS,
    [ROLE_INVENTORY_MANAGER],
)
def list_transfers_planned_all() -> None:
    conn = get_conn()

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """ SELECT  t.id, t.from_warehouse_id, t.to_warehouse_id,
                                ti.requested_by, ti.status,
                                ti.product_id, p.name AS product_name,
                                ti.quantity, ti.reserve_id,
                                o.id AS order_id
                        FROM inventory.transfers t
                        JOIN inventory.transfer_items ti ON ti.transfer_id = t.id
                        JOIN catalog.products p ON ti.product_id = p.id
                        LEFT JOIN inventory.reserves r ON ti.reserve_id = r.id
                        LEFT JOIN sales.orders o ON r.order_id = o.id
                        WHERE t.status = 'planned'
                        ORDER BY t.from_warehouse_id, t.to_warehouse_id, t.id, p.name"""
        )
        rows: list[dict] = cur.fetchall()

    if not rows:
        console.print("[yellow]Нет planned перемещений[/yellow]")
        return

    # Группируем по маршруту (один planned transfer на маршрут — unique index)
    route_groups: dict[tuple[int, int], list[dict]] = {}
    route_order: list[tuple[int, int]] = []
    for row in rows:
        key = (row["from_warehouse_id"], row["to_warehouse_id"])
        if key not in route_groups:
            route_groups[key] = []
            route_order.append(key)
        route_groups[key].append(row)

    for (from_wh_id, to_wh_id), items in route_groups.items():
        from_address = get_warehouse_full_address(from_wh_id)
        to_address = get_warehouse_full_address(to_wh_id)

        transfer_id = items[0]["id"]
        console.print(
            f"\n[bold]Маршрут: {from_address} → {to_address}"
            f" (Трансфер #{transfer_id})[/bold]"
        )

        transfer = Transfer(
            id=transfer_id,
            from_warehouse_id=from_wh_id,
            to_warehouse_id=to_wh_id,
            status="planned",
            created_at=datetime.now(),
            started_at=None,
            arriving_at=None,
            received_at=None,
        )
        _render_transfer_items(transfer, items)


@command(
    "list transfers planned my",
    "мои запланированные перемещения",
    CATEGORY_TRANSFERS,
    [ROLE_INVENTORY_MANAGER],
)
def list_transfers_planned_my() -> None:
    current_user = auth_user()
    conn = get_conn()

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """SELECT t.id, t.from_warehouse_id, t.to_warehouse_id,
                      ti.requested_by, ti.status,
                      ti.product_id, p.name AS product_name,
                      ti.quantity, ti.reserve_id,
                      o.id AS order_id
               FROM inventory.transfers t
               JOIN inventory.transfer_items ti ON ti.transfer_id = t.id
               JOIN catalog.products p ON ti.product_id = p.id
               LEFT JOIN inventory.reserves r ON ti.reserve_id = r.id
               LEFT JOIN sales.orders o ON r.order_id = o.id
               WHERE t.status = 'planned' AND ti.requested_by = %s
               ORDER BY t.from_warehouse_id, t.to_warehouse_id, t.id, p.name""",
            (current_user.id,),
        )
        rows: list[dict] = cur.fetchall()

    if not rows:
        console.print("[yellow]У вас нет запланированных перемещений[/yellow]")
        return

    route_groups: dict[tuple[int, int], list[dict]] = {}
    route_order: list[tuple[int, int]] = []
    for row in rows:
        key = (row["from_warehouse_id"], row["to_warehouse_id"])
        if key not in route_groups:
            route_groups[key] = []
            route_order.append(key)
        route_groups[key].append(row)

    for (from_wh_id, to_wh_id), items in route_groups.items():
        from_address = get_warehouse_full_address(from_wh_id)
        to_address = get_warehouse_full_address(to_wh_id)

        transfer_id = items[0]["id"]
        console.print(
            f"\n[bold]Маршрут: {from_address} → {to_address}"
            f" (Трансфер #{transfer_id})[/bold]"
        )

        transfer = Transfer(
            id=transfer_id,
            from_warehouse_id=from_wh_id,
            to_warehouse_id=to_wh_id,
            status="planned",
            created_at=datetime.now(),
            started_at=None,
            arriving_at=None,
            received_at=None,
        )
        _render_transfer_items(transfer, items)


@command(
    "add transfer items",
    "добавить товары в перемещение (интерактивно)",
    CATEGORY_TRANSFERS,
    [ROLE_INVENTORY_MANAGER],
)
def add_transfer_items() -> None:
    """Интерактивное добавление товаров в planned transfer.

    Интерактивная часть (prompt) выполняется вне транзакции, чтобы
    блокировки FOR UPDATE не удерживались во время ожидания ввода.
    SQL-операции (поиск/создание трансфера, проверка стока, INSERT)
    остаются внутри транзакции.
    """
    conn = get_conn()

    # Маппинг: склад-отправление -> [склады-получатели, доступные по маршрутам]
    route_pairs = _get_route_pairs()
    if not route_pairs:
        render_error("Нет маршрутов. Сначала добавьте маршруты.")
        return

    warehouses = get_warehouses()
    warehouses_by_id = {w.id: w for w in warehouses}

    from_warehouses = [
        warehouses_by_id[wid] for wid in route_pairs if wid in warehouses_by_id
    ]
    from_warehouses_options = [
        (w.id, f"{get_warehouse_full_address(w.city_id)}, {w.address}")
        for w in from_warehouses
    ]

    from_wh_id = prompt_choice(
        message="Выберите склад отправления:",
        options=from_warehouses_options,
    )

    # Только те склады, в которые есть маршрут из выбранного отправления
    to_wh_ids = route_pairs.get(from_wh_id, [])
    to_warehouses = [
        warehouses_by_id[wid]
        for wid in to_wh_ids
        if wid in warehouses_by_id and wid != from_wh_id
    ]
    to_warehouses_options = [
        (w.id, f"{get_warehouse_full_address(w.city_id)}, {w.address}")
        for w in to_warehouses
    ]

    if not to_warehouses:
        render_error(
            f"Из склада {get_warehouse_full_address(from_wh_id)} "
            f"нет маршрутов никуда."
        )
        return

    to_wh_id = prompt_choice(
        message="Выберите склад получения:",
        options=to_warehouses_options,
    )

    transfer_id = None

    # Поиск/создание трансфера — в одной транзакции (атомарно)
    with conn.transaction():
        cur = conn.cursor()
        cur.execute(
            """SELECT id FROM inventory.transfers
               WHERE from_warehouse_id = %s AND to_warehouse_id = %s AND status = 'planned'
               FOR UPDATE""",
            (from_wh_id, to_wh_id),
        )
        existing = cur.fetchone()

        if existing:
            transfer_id = existing[0]
            console.print(f"[green]Найден существующий transfer #{transfer_id}[/green]")
        else:
            try:
                transfer_id = conn.execute(
                    """INSERT INTO inventory.transfers
                       (from_warehouse_id, to_warehouse_id, status)
                       VALUES (%s, %s, 'planned') RETURNING id""",
                    (from_wh_id, to_wh_id),
                ).fetchone()[0]
                console.print(f"[green]Создан трансфер #{transfer_id}[/green]")
            except UniqueViolation:
                cur.execute(
                    """SELECT id FROM inventory.transfers
                       WHERE from_warehouse_id = %s AND to_warehouse_id = %s AND status = 'planned'
                       FOR UPDATE""",
                    (from_wh_id, to_wh_id),
                )
                row = cur.fetchone()
                if row is None:
                    render_error("Ошибка: трансфер не найден после вставки")
                    return
                transfer_id = row[0]

    while True:  # ← цикл ВНУТРИ, промпты ВНЕ транзакции
        # 1. Список стока склада отправления — вне транзакции
        with conn.cursor() as cur:
            cur.execute(
                """SELECT s.product_id, p.name, p.sku, s.quantity
                   FROM inventory.stock s
                   JOIN catalog.products p ON s.product_id = p.id
                   WHERE s.warehouse_id = %s
                   ORDER BY p.name""",
                (from_wh_id,),
            )
            stock_rows = cur.fetchall()

        if not stock_rows:
            console.print("[yellow]На складе нет товаров[/yellow]")
            break

        product_options = [
            (row[0], f"{row[1]} ({row[2]}) — сток: {row[3]}") for row in stock_rows
        ]

        # 2. Все промпты — ВНЕ транзакции
        product_id = prompt_choice(
            message="Выберите товар (или 'Отмена'):",
            options=product_options,
        )
        if product_id is None or product_id == "Отмена":
            break

        quantity_str = prompt(
            "Количество: ",
            validator=QuantityValidator(),
        )
        quantity = int(quantity_str)

        answer = prompt(
            f"Добавить {quantity} шт. в трансфер #{transfer_id}? (y/n, д/н): ",
            validator=YesNoValidator(),
        )
        if not YesNoValidator.is_yes(answer):
            continue

        # 3. Проверка стока + INSERT — короткая транзакция
        with conn.transaction():
            # Блокируем трансфер и проверяем, что он всё ещё planned
            with conn.cursor(row_factory=dict_row) as transfer_lock_cur:
                transfer_lock_cur.execute(
                    """SELECT status FROM inventory.transfers
                       WHERE id = %s FOR UPDATE""",
                    (transfer_id,),
                )
                transfer_row = transfer_lock_cur.fetchone()
                if transfer_row is None or transfer_row["status"] != "planned":
                    render_error(
                        f"Трансфер #{transfer_id} уже не в статусе planned — "
                        f"добавление невозможно."
                    )
                    continue

            # Блокируем строку stock — FOR UPDATE
            with conn.cursor(row_factory=dict_row) as check_cur:
                check_cur.execute(
                    """SELECT s.quantity
                       FROM inventory.stock s
                       WHERE s.warehouse_id = %s AND s.product_id = %s
                       FOR UPDATE""",
                    (from_wh_id, product_id),
                )
                stock_row = check_cur.fetchone()
                if stock_row is None or stock_row["quantity"] < quantity:
                    render_error(
                        f"На складе недостаточно товара: "
                        f"доступно {stock_row['quantity'] if stock_row else 0} шт., "
                        f"нужно {quantity} шт."
                    )
                    continue

            # Блокируем строку transfer_items — FOR UPDATE
            with conn.cursor() as lock_cur:
                lock_cur.execute(
                    """SELECT 1 FROM inventory.transfer_items
                       WHERE transfer_id = %s AND product_id = %s AND requested_by = %s
                         AND reserve_id IS NULL
                       FOR UPDATE""",
                    (transfer_id, product_id, auth_user().id),
                )
                lock_cur.fetchone()  # consume — блокировка активна пока cursor жив

            # INSERT transfer_items + UPDATE stock
            try:
                conn.execute(
                    """INSERT INTO inventory.transfer_items
                       (transfer_id, product_id, quantity, requested_by)
                       VALUES (%s, %s, %s, %s)""",
                    (transfer_id, product_id, quantity, auth_user().id),
                )

                conn.execute(
                    """UPDATE inventory.stock SET quantity = quantity - %s
                       WHERE warehouse_id = %s AND product_id = %s""",
                    (quantity, from_wh_id, product_id),
                )
                console.print(f"[green]Добавлено {quantity} шт.[/green]")

            except UniqueViolation:
                conn.execute(
                    """UPDATE inventory.transfer_items
                       SET quantity = quantity + %s
                       WHERE transfer_id = %s AND product_id = %s
                         AND requested_by = %s AND reserve_id IS NULL""",
                    (quantity, transfer_id, product_id, auth_user().id),
                )
                conn.execute(
                    """UPDATE inventory.stock SET quantity = quantity - %s
                       WHERE warehouse_id = %s AND product_id = %s""",
                    (quantity, from_wh_id, product_id),
                )
                console.print(f"[green]Обновлено: добавлено ещё {quantity} шт.[/green]")

        # "Добавить ещё?" — ВНЕ транзакции
        answer = prompt(
            "Добавить ещё? (y/n, д/н): ",
            validator=YesNoValidator(),
        )
        if not YesNoValidator.is_yes(answer):
            break

    console.print(f"[green]Трансфер #{transfer_id} готов[/green]")
    _render_transfer_items(
        Transfer(
            id=transfer_id,
            from_warehouse_id=from_wh_id,
            to_warehouse_id=to_wh_id,
            status="planned",
            created_at=datetime.now(),
            started_at=None,
            arriving_at=None,
            received_at=None,
        ),
        [],
    )


@command(
    "remove transfer items",
    "удалить товары из трансфера (интерактивно)",
    CATEGORY_TRANSFERS,
    [ROLE_INVENTORY_MANAGER],
)
def remove_transfer_items() -> None:
    """Интерактивное удаление товаров из planned transfer.

    Интерактивная часть (prompt) выполняется вне транзакции, чтобы
    блокировки FOR UPDATE не удерживались во время ожидания ввода.
    SQL-операции (блокировка, UPDATE/DELETE) остаются внутри транзакции.
    Использует while True вместо рекурсии — рекурсия внутри
    conn.transaction() вызывает InFailedSqlTransaction в psycopg3.
    """
    conn = get_conn()

    # Список planned transfer-ов с хотя бы одним item
    with conn.cursor(row_factory=class_row(Transfer)) as cur:
        cur.execute("""SELECT t.* FROM inventory.transfers t
               WHERE t.status = 'planned'
                 AND EXISTS (SELECT 1 FROM inventory.transfer_items ti WHERE ti.transfer_id = t.id)
               ORDER BY t.from_warehouse_id, t.to_warehouse_id, t.id""")
        transfers: list[Transfer] = cur.fetchall()

    if not transfers:
        console.print("[yellow]Нет перемещений с товарами[/yellow]")
        return

    transfer_options = [
        (
            t.id,
            f"#{t.id}: {get_warehouse_full_address(t.from_warehouse_id)} → {get_warehouse_full_address(t.to_warehouse_id)}",
        )
        for t in transfers
    ]

    transfer_id = prompt_choice(
        message="Выберите трансфер:",
        options=transfer_options,
    )

    if transfer_id is None:
        return

    while True:  # ← вместо рекурсии
        # 1. Блокировка и чтение данных — ВНУТРИ транзакции
        with conn.transaction():
            # Блокируем transfer
            cur = conn.cursor()
            cur.execute(
                """SELECT id FROM inventory.transfers
                   WHERE id = %s AND status = 'planned'
                   FOR UPDATE""",
                (transfer_id,),
            )
            if cur.fetchone() is None:
                render_error(
                    f"Трансфер #{transfer_id} не найден или не в статусе planned"
                )
                return

            # Список items в transfer
            with conn.cursor(row_factory=class_row(TransferItem)) as cur:
                cur.execute(
                    """SELECT * FROM inventory.transfer_items
                       WHERE transfer_id = %s
                       ORDER BY product_id""",
                    (transfer_id,),
                )
                items: list[TransferItem] = cur.fetchall()

            if not items:
                render_error(f"В трансфере #{transfer_id} нет товаров")
                return

            item_options = [
                (i.id, f"ID {i.product_id} — {i.quantity} шт.") for i in items
            ]

        # 2. Все промпты — ВНЕ транзакции
        item_id = prompt_choice(
            message="Выберите товар для удаления (или 'Отмена'):",
            options=item_options,
        )
        if item_id is None or item_id == "Отмена":
            return

        item = next((i for i in items if i.id == int(item_id)), None)
        if item is None:
            render_error(f"Товар #{item_id} не найден")
            return

        remove_qty_str = prompt(
            f"Количество для удаления (макс. {item.quantity}): ",
            validator=QuantityValidator(),
        )
        remove_qty = int(remove_qty_str)

        if remove_qty > item.quantity:
            render_error(f"Нельзя удалить больше {item.quantity} шт.")
            return

        answer = prompt(
            f"Удалить {remove_qty} шт. из transfer #{transfer_id}? (y/n, д/н): ",
            validator=YesNoValidator(),
        )
        if not YesNoValidator.is_yes(answer):
            return

        # 3. Блокировка и модификация — ВНУТРИ транзакции
        with conn.transaction():
            # Блокируем строку transfer_items
            with conn.cursor() as lock_cur:
                lock_cur.execute(
                    """SELECT id FROM inventory.transfer_items
                       WHERE transfer_id = %s AND product_id = %s
                       FOR UPDATE""",
                    (transfer_id, item.product_id),
                )
                lock_cur.fetchone()  # consume — блокировка активна пока cursor жив

            cur = conn.cursor()
            cur.execute(
                """UPDATE inventory.transfer_items
                   SET quantity = quantity - %s
                   WHERE transfer_id = %s AND product_id = %s AND quantity >= %s
                   RETURNING quantity""",
                (remove_qty, transfer_id, item.product_id, remove_qty),
            )
            new_qty = cur.fetchone()
            if new_qty is None:
                render_error("Невозможно удалить такое количество")
                return

            # Возвращаем quantity в stock
            cur.execute(
                """UPDATE inventory.stock SET quantity = quantity + %s
                   WHERE warehouse_id = (SELECT from_warehouse_id FROM inventory.transfers WHERE id = %s)
                     AND product_id = %s""",
                (remove_qty, transfer_id, item.product_id),
            )

            # Если quantity = 0, удаляем item
            if new_qty[0] == 0:
                conn.execute(
                    "DELETE FROM inventory.transfer_items WHERE id = %s",
                    (int(item_id),),
                )
                console.print(f"[green]Товар удалён из transfer #{transfer_id}[/green]")
            else:
                console.print(
                    f"[green]Удалено {remove_qty} шт., осталось {new_qty[0]} шт.[/green]"
                )

        # "Удалить ещё?" — ВНЕ транзакции
        answer = prompt("Удалить ещё? (y/n, д/н): ", validator=YesNoValidator())
        if not YesNoValidator.is_yes(answer):
            break


@command(
    "start shipping",
    "начать отгрузку трансфера",
    CATEGORY_TRANSFERS,
    [ROLE_INVENTORY_MANAGER],
)
def start_shipping(transfer_id: str) -> None:
    """Изменяет статус перемещения с planned на shipping."""
    conn = get_conn()

    with conn.transaction():
        cur = conn.cursor()
        cur.execute(
            """SELECT id, status FROM inventory.transfers WHERE id = %s FOR UPDATE""",
            (transfer_id,),
        )
        row = cur.fetchone()
        if row is None:
            render_error(f"Трансфер #{transfer_id} не найден")
            return
        if row[1] != "planned":
            render_error(
                f"Трансфер #{transfer_id} имеет статус '{row[1]}', а не 'planned'"
            )
            return

        # Обновляем статус transfer
        conn.execute(
            """UPDATE inventory.transfers
               SET status = 'shipping', started_at = NOW(), arriving_at = NOW() + INTERVAL '1 day'
               WHERE id = %s""",
            (transfer_id,),
        )

        # Обновляем статус всех transfer_items на 'shipped'
        conn.execute(
            """UPDATE inventory.transfer_items
               SET status = 'shipped' WHERE transfer_id = %s""",
            (transfer_id,),
        )

    console.print(f"[green]Трансфер #{transfer_id} отправлен в доставку[/green]")
