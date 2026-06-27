from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from psycopg.rows import class_row
from rich.panel import Panel
from rich.table import Table

from auth import ROLE_INVENTORY_MANAGER
from commands import command, CATEGORY_ROUTES
from console import console, render_error
from db import get_conn
from structures import Route
from validators import ChoiceValidator, NonEmptyValidator, YesNoValidator, PriceValidator


def _get_city_options() -> list[tuple[int, str]]:
    """Return list of (city_id, city_name) for use in choice prompts."""
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT id, name FROM catalog.cities ORDER BY id")
        rows = cur.fetchall()
    return [(row[0], row[1]) for row in rows]


def _get_route_options():
    """Return (display_strings, route_map) for dropdown route selection."""
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT r.from_city_id, r.to_city_id, c_from.name, c_to.name
            FROM inventory.routes r
            JOIN catalog.cities c_from ON r.from_city_id = c_from.id
            JOIN catalog.cities c_to ON r.to_city_id = c_to.id
            ORDER BY r.from_city_id, r.to_city_id
        """)
        routes = cur.fetchall()
    display_strings = [f"{row[2]} → {row[3]}" for row in routes]
    route_map = {ds: (row[0], row[1]) for ds, row in zip(display_strings, routes)}
    return display_strings, route_map


def _format_duration(td) -> str:
    """Format timedelta as MM:SS."""
    total_seconds = int(td.total_seconds())
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes:02d}:{seconds:02d}"


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

    with conn.cursor() as cur:
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
    city_map = {c[0]: c[1] for c in cities}

    route_options, route_map = _get_route_options()

    if not route_options:
        render_error("Маршруты не найдены")
        return

    route_completer = WordCompleter(route_options, ignore_case=True, sentence=True)
    route_validator = ChoiceValidator(
        route_options, message="Пожалуйста, выберите маршрут из списка. Используйте Tab для автодополнения."
    )
    selected_str = prompt(
        "Выберите маршрут: ", validator=route_validator, completer=route_completer
    ).strip()

    from_city_id, to_city_id = route_map[selected_str]

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

    _render_route(route, city_map.get(from_city_id, "?"), city_map.get(to_city_id, "?"))


@command("add route", "добавить маршрут", CATEGORY_ROUTES, [ROLE_INVENTORY_MANAGER])
def add_route() -> None:
    conn = get_conn()
    cities = _get_city_options()

    # Find already existing routes
    with conn.cursor() as cur:
        cur.execute("""
            SELECT from_city_id, to_city_id FROM inventory.routes ORDER BY from_city_id, to_city_id
        """)
        existing_routes = set(cur.fetchall())

    city_names = [c[1] for c in cities]
    city_map = {c[1]: c[0] for c in cities}

    # Pick from city — dropdown with Tab auto-completion
    from_completer = WordCompleter(city_names, ignore_case=True, sentence=True)
    from_validator = ChoiceValidator(
        city_names, message="Город должен быть из списка. Используйте Tab для автодополнения."
    )
    from_name = prompt(
        "Город отправления: ", validator=from_validator, completer=from_completer
    ).strip()

    # Pick to city — exclude same city; validate pair not already routed
    to_candidates = [name for name in city_names if name != from_name]
    to_completer = WordCompleter(to_candidates, ignore_case=True, sentence=True)
    to_validator = ChoiceValidator(
        to_candidates, message="Город должен быть из списка. Используйте Tab для автодополнения."
    )
    to_name = prompt(
        "Город назначения: ", validator=to_validator, completer=to_completer
    ).strip()

    from_city_id = city_map[from_name]
    to_city_id = city_map[to_name]

    if (from_city_id, to_city_id) in existing_routes:
        render_error(f"Маршрут {from_name} → {to_name} уже существует")
        return

    duration_str = prompt(
        "Длительность (MM:SS): ", validator=NonEmptyValidator()
    ).strip()
    parts = list(map(int, duration_str.split(":")))
    if len(parts) == 2:
        total_seconds = parts[0] * 60 + parts[1]
    else:
        render_error("Неверный формат длительности. Используйте MM:SS")
        return

    threshold = prompt(
        "Минимальная стоимость перемещения: ", validator=NonEmptyValidator()
    ).strip()

    conn.execute(
        """INSERT INTO inventory.routes (from_city_id, to_city_id, duration, total_threshold)
           VALUES (%s, %s, %s * INTERVAL '1 second', %s)""",
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

    route_options, route_map = _get_route_options()

    if not route_options:
        render_error("Маршруты не найдены")
        return

    route_completer = WordCompleter(route_options, ignore_case=True, sentence=True)
    route_validator = ChoiceValidator(
        route_options, message="Пожалуйста, выберите маршрут из списка. Используйте Tab для автодополнения."
    )
    selected_str = prompt(
        "Выберите маршрут для редактирования: ",
        validator=route_validator,
        completer=route_completer,
    ).strip()

    from_city_id, to_city_id = route_map[selected_str]

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

    from_name = city_map.get(from_city_id, "?")
    to_name = city_map.get(to_city_id, "?")

    duration_str = prompt(
        "Длительность (MM:SS): ",
        default=_format_duration(route.duration),
        validator=NonEmptyValidator(),
    ).strip()
    parts = list(map(int, duration_str.split(":")))
    if len(parts) == 2:
        total_seconds = parts[0] * 60 + parts[1]
    else:
        render_error("Неверный формат длительности. Используйте MM:SS")
        return

    threshold = prompt(
        "Минимальная стоимость перемещения: ",
        default=str(route.total_threshold),
        validator=PriceValidator(),
    ).strip()

    conn.execute(
        """UPDATE inventory.routes
           SET duration = %s * INTERVAL '1 second', total_threshold = %s
           WHERE from_city_id = %s AND to_city_id = %s""",
        (total_seconds, threshold, from_city_id, to_city_id),
    )

    console.print(
        f"[green]Маршрут {from_name} → {to_name} обновлен [/green]"
    )


@command("delete route", "удалить маршрут", CATEGORY_ROUTES, [ROLE_INVENTORY_MANAGER])
def delete_route() -> None:
    conn = get_conn()
    cities = _get_city_options()
    city_map = {c[0]: c[1] for c in cities}

    route_options, route_map = _get_route_options()

    if not route_options:
        render_error("Маршруты не найдены")
        return

    route_completer = WordCompleter(route_options, ignore_case=True, sentence=True)
    route_validator = ChoiceValidator(
        route_options, message="Пожалуйста, выберите маршрут из списка. Используйте Tab для автодополнения."
    )
    selected_str = prompt(
        "Выберите маршрут для удаления: ",
        validator=route_validator,
        completer=route_completer,
    ).strip()

    from_city_id, to_city_id = route_map[selected_str]
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
