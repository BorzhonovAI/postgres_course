from prompt_toolkit import prompt
from prompt_toolkit.shortcuts import choice
from psycopg.rows import class_row, scalar_row
from rich.panel import Panel
from rich.table import Table

from auth import ROLE_INVENTORY_MANAGER
from commands import command, CATEGORY_ROUTES
from console import console, render_error
from db import get_conn
from structures import Route
from validators import NonEmptyValidator, YesNoValidator


def _get_city_options() -> list[tuple[int, str]]:
    """Return list of (city_id, city_name) for use in choice prompts."""
    conn = get_conn()
    with conn.cursor(row_factory=scalar_row) as cur:
        cur.execute("SELECT id, name FROM catalog.cities ORDER BY id")
        rows = cur.fetchall()
    return [(row[0], row[1]) for row in rows]


def _format_duration(td) -> str:
    """Format timedelta as HH:MM:SS."""
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _render_route(route: Route, from_name: str, to_name: str) -> None:
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Поле", style="bold cyan", width=20)
    table.add_column("Значение", style="white")
    table.add_row("От города", from_name)
    table.add_row("До города", to_name)
    table.add_row("Длительность", _format_duration(route.duration))
    table.add_row("Мин. стоимость", str(route.total_threshold))

    panel = Panel(
        table,
        expand=False,
        title=f"[bold green]Маршрут {from_name} → {to_name}[/bold green]",
        border_style="green",
    )
    console.print(panel)


@command(
    "list routes", "список всех маршрутов", CATEGORY_ROUTES, [ROLE_INVENTORY_MANAGER]
)
def list_routes() -> None:
    conn = get_conn()
    table = Table(title="Маршруты", show_header=True, header_style="bold cyan")
    table.add_column("От", style="green", min_width=15)
    table.add_column("До", style="yellow", min_width=15)
    table.add_column("Длительность", style="magenta", min_width=15)
    table.add_column("Мин. стоимость", style="red", min_width=15)

    with conn.cursor(row_factory=scalar_row) as cur:
        cur.execute("""
            SELECT r.duration, r.total_threshold, c_from.name, c_to.name
            FROM inventory.routes r
            JOIN catalog.cities c_from ON r.from_city_id = c_from.id
            JOIN catalog.cities c_to ON r.to_city_id = c_to.id
            ORDER BY r.from_city_id, r.to_city_id
        """)
        rows = cur.fetchall()

    for row in rows:
        table.add_row(
            row[2],  # from city name
            row[3],  # to city name
            _format_duration(row[0]),
            str(row[1]),
        )
    console.print(table)


@command(
    "show route", "информация о маршруте", CATEGORY_ROUTES, [ROLE_INVENTORY_MANAGER]
)
def show_route() -> None:
    conn = get_conn()
    cities = _get_city_options()

    # Get existing routes to pick from
    with conn.cursor(row_factory=scalar_row) as cur:
        cur.execute("""
            SELECT r.from_city_id, r.to_city_id, c_from.name, c_to.name
            FROM inventory.routes r
            JOIN catalog.cities c_from ON r.from_city_id = c_from.id
            JOIN catalog.cities c_to ON r.to_city_id = c_to.id
            ORDER BY r.from_city_id, r.to_city_id
        """)
        routes = cur.fetchall()

    if not routes:
        render_error("Маршруты не найдены")
        return

    route_options = [(idx, f"{row[2]} → {row[3]}") for idx, row in enumerate(routes)]

    selected = choice(
        message="Выберите маршрут:",
        options=route_options,
    )

    from_city_id, to_city_id = routes[selected][0], routes[selected][1]

    with conn.cursor(row_factory=class_row(Route)) as cur:
        cur.execute(
            """
            SELECT from_city_id, to_city_id, duration, total_threshold
            FROM inventory.routes
            WHERE from_city_id = %s AND to_city_id = %s
        """,
            (from_city_id, to_city_id),
        )
        route: Route | None = cur.fetchone()

    if not route:
        render_error("Маршрут не найден")
        return

    city_map = {c[0]: c[1] for c in cities}
    _render_route(route, city_map.get(from_city_id, "?"), city_map.get(to_city_id, "?"))


@command("add route", "добавить маршрут", CATEGORY_ROUTES, [ROLE_INVENTORY_MANAGER])
def add_route() -> None:
    conn = get_conn()
    cities = _get_city_options()

    # Find cities already used in routes
    with conn.cursor(row_factory=scalar_row) as cur:
        cur.execute("""
            SELECT from_city_id, to_city_id FROM inventory.routes ORDER BY from_city_id, to_city_id
        """)
        existing_routes = set(cur.fetchall())

    # Show available city pairs not yet routed
    available_pairs = [
        (f"{c_from[1]}", f"{c_to[1]}")
        for c_from in cities
        for c_to in cities
        if c_from[0] != c_to[0] and (c_from[0], c_to[0]) not in existing_routes
    ]

    if not available_pairs:
        render_error("Все возможные маршруты уже добавлены")
        return

    # Pick from city
    from_city_names = [name for name, _ in available_pairs]
    from_choice_items = list(set(from_city_names))
    from_choice_items.sort()
    from_options = [(i, name) for i, name in enumerate(from_choice_items)]

    from_selected = choice(
        message="Город отправления:",
        options=from_options,
    )
    from_name = from_choice_items[from_selected]

    # Pick to city (exclude same city and already routed pairs)
    to_options_filtered = [
        name for name, to_name in available_pairs if name == from_name
    ]
    to_options = [(i, name) for i, name in enumerate(to_options_filtered)]

    to_selected = choice(
        message="Город назначения:",
        options=to_options,
    )
    to_name = to_options_filtered[to_selected]

    city_map = {c[1]: c[0] for c in cities}
    from_city_id = city_map[from_name]
    to_city_id = city_map[to_name]

    duration_str = prompt(
        "Длительность (HH:MM:SS): ", validator=NonEmptyValidator()
    ).strip()
    parts = list(map(int, duration_str.split(":")))
    if len(parts) == 3:
        total_seconds = parts[0] * 3600 + parts[1] * 60 + parts[2]
    elif len(parts) == 2:
        total_seconds = parts[0] * 60 + parts[1]
    else:
        render_error("Неверный формат длительности. Используйте HH:MM:SS или MM:SS")
        return

    threshold = prompt(
        "Минимальная стоимость перемещения: ", validator=NonEmptyValidator()
    ).strip()

    conn.execute(
        """INSERT INTO inventory.routes (from_city_id, to_city_id, duration, total_threshold)
           VALUES (%s, %s, INTERVAL '%s seconds', %s)""",
        (from_city_id, to_city_id, total_seconds, threshold),
    )

    console.print(f"[green]Маршрут {from_name} → {to_name} добавлен [/green]")


@command(
    "edit route", "редактировать маршрут", CATEGORY_ROUTES, [ROLE_INVENTORY_MANAGER]
)
def edit_route() -> None:
    conn = get_conn()
    cities = _get_city_options()
    city_map = {c[0]: c[1] for c in cities}

    with conn.cursor(row_factory=scalar_row) as cur:
        cur.execute("""
            SELECT r.from_city_id, r.to_city_id, c_from.name, c_to.name
            FROM inventory.routes r
            JOIN catalog.cities c_from ON r.from_city_id = c_from.id
            JOIN catalog.cities c_to ON r.to_city_id = c_to.id
            ORDER BY r.from_city_id, r.to_city_id
        """)
        routes = cur.fetchall()

    if not routes:
        render_error("Маршруты не найдены")
        return

    route_options = [(idx, f"{row[2]} → {row[3]}") for idx, row in enumerate(routes)]

    selected = choice(
        message="Выберите маршрут для редактирования:",
        options=route_options,
    )

    from_city_id, to_city_id = routes[selected][0], routes[selected][1]
    from_name = city_map.get(from_city_id, "?")
    to_name = city_map.get(to_city_id, "?")

    # Get current values
    with conn.cursor(row_factory=class_row(Route)) as cur:
        cur.execute(
            """
            SELECT from_city_id, to_city_id, duration, total_threshold
            FROM inventory.routes
            WHERE from_city_id = %s AND to_city_id = %s
        """,
            (from_city_id, to_city_id),
        )
        route: Route | None = cur.fetchone()

    if not route:
        render_error("Маршрут не найден")
        return

    # Edit from city
    from_options = [(c[0], c[1]) for c in cities if c[0] != to_city_id]
    new_from_id = choice(
        message="Город отправления:",
        options=from_options,
        default=route.from_city_id,
    )

    # Edit to city
    to_options = [(c[0], c[1]) for c in cities if c[0] != new_from_id]
    new_to_id = choice(
        message="Город назначения:",
        options=to_options,
        default=route.to_city_id,
    )

    duration_str = prompt(
        "Длительность (HH:MM:SS): ",
        default=_format_duration(route.duration),
        validator=NonEmptyValidator(),
    ).strip()
    parts = list(map(int, duration_str.split(":")))
    if len(parts) == 3:
        total_seconds = parts[0] * 3600 + parts[1] * 60 + parts[2]
    elif len(parts) == 2:
        total_seconds = parts[0] * 60 + parts[1]
    else:
        render_error("Неверный формат длительности. Используйте HH:MM:SS или MM:SS")
        return

    threshold = prompt(
        "Минимальная стоимость перемещения: ",
        default=str(route.total_threshold),
        validator=NonEmptyValidator(),
    ).strip()

    conn.execute(
        """UPDATE inventory.routes
           SET from_city_id = %s, to_city_id = %s, duration = INTERVAL '%s seconds', total_threshold = %s
           WHERE from_city_id = %s AND to_city_id = %s""",
        (new_from_id, new_to_id, total_seconds, threshold, from_city_id, to_city_id),
    )

    console.print(
        f"[green]Маршрут {city_map.get(new_from_id)} → {city_map.get(new_to_id)} обновлен [/green]"
    )


@command("delete route", "удалить маршрут", CATEGORY_ROUTES, [ROLE_INVENTORY_MANAGER])
def delete_route() -> None:
    conn = get_conn()
    cities = _get_city_options()
    city_map = {c[0]: c[1] for c in cities}

    with conn.cursor(row_factory=scalar_row) as cur:
        cur.execute("""
            SELECT r.from_city_id, r.to_city_id, c_from.name, c_to.name
            FROM inventory.routes r
            JOIN catalog.cities c_from ON r.from_city_id = c_from.id
            JOIN catalog.cities c_to ON r.to_city_id = c_to.id
            ORDER BY r.from_city_id, r.to_city_id
        """)
        routes = cur.fetchall()

    if not routes:
        render_error("Маршруты не найдены")
        return

    route_options = [(idx, f"{row[2]} → {row[3]}") for idx, row in enumerate(routes)]

    selected = choice(
        message="Выберите маршрут для удаления:",
        options=route_options,
    )

    from_city_id, to_city_id = routes[selected][0], routes[selected][1]
    from_name = city_map.get(from_city_id, "?")
    to_name = city_map.get(to_city_id, "?")

    with conn.cursor(row_factory=class_row(Route)) as cur:
        cur.execute(
            """
            SELECT from_city_id, to_city_id, duration, total_threshold
            FROM inventory.routes
            WHERE from_city_id = %s AND to_city_id = %s
        """,
            (from_city_id, to_city_id),
        )
        route: Route | None = cur.fetchone()

    if not route:
        render_error("Маршрут не найден")
        return

    _render_route(route, from_name, to_name)

    answer = prompt("Вы уверены? (y/n, д/н): ", validator=YesNoValidator())

    if YesNoValidator.is_yes(answer):
        conn.execute(
            """DELETE FROM inventory.routes
               WHERE from_city_id = %s AND to_city_id = %s""",
            (from_city_id, to_city_id),
        )
        console.print(f"[green]Маршрут {from_name} → {to_name} удален [/green]")
