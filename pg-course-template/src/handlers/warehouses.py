from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from psycopg.rows import class_row, scalar_row
from rich.panel import Panel
from rich.table import Table

from auth import ALL_ROLES, ROLE_CATALOG_MANAGER
from commands import command, CATEGORY_WAREHOUSES
from console import console, render_error
from db import get_conn
from .structures import Warehouse
from validators import ChoiceValidator, NonEmptyValidator, YesNoValidator


def get_cities_names() -> list[str]:
    conn = get_conn()
    with conn.cursor(row_factory=scalar_row) as cur:
        cur.execute("SELECT name FROM catalog.cities")
        names_list: list[str] = cur.fetchall()

    return names_list


def get_warehouse_by_id(_id: int) -> Warehouse | None:
    conn = get_conn()
    with conn.cursor(row_factory=class_row(Warehouse)) as cur:
        cur.execute("SELECT * FROM catalog.warehouses WHERE id = %s", (_id,))
        warehouse: Warehouse | None = cur.fetchone()

    return warehouse


def get_city_name(_id: int) -> str:
    conn = get_conn()
    with conn.cursor(row_factory=scalar_row) as cur:
        cur.execute("SELECT name FROM catalog.cities WHERE id = %s", (_id,))
        name: str = cur.fetchone()

    return name


def get_city_id(name: str) -> int:
    conn = get_conn()
    with conn.cursor(row_factory=scalar_row) as cur:
        cur.execute("SELECT id FROM catalog.cities WHERE name = %s", (name,))
        id_: int = cur.fetchone()

    return id_


# Использовать только при полной уверенности в существовании склада
def get_warehouse_full_address(_id: int) -> str:
    warehouse = get_warehouse_by_id(_id)
    city = get_city_name(warehouse.city_id)
    return f"г. {city}, {warehouse.address}"


def get_warehouses() -> list[Warehouse]:
    conn = get_conn()
    with conn.cursor(row_factory=class_row(Warehouse)) as cur:
        cur.execute("SELECT * FROM catalog.warehouses")
        warehouses: list[Warehouse] = cur.fetchall()

    return warehouses


def _render_warehouse(warehouse: Warehouse) -> None:
    table = Table(show_header=False, box=None, padding=(0, 2))

    table.add_column("Поле", style="bold cyan", width=15)
    table.add_column("Значение", style="white")

    table.add_row("ID", str(warehouse.id))
    table.add_row("Город", get_city_name(warehouse.city_id))
    table.add_row("Адрес", warehouse.address)
    table.add_row("Метка", warehouse.label or "")
    table.add_row("Центральный", "да" if warehouse.is_central else "нет")

    panel = Panel(
        table,
        expand=False,
        title=f"[bold green]Склад #{warehouse.id}[/bold green]",
        border_style="green",
    )

    console.print(panel)


@command("list warehouses", "список всех складов", CATEGORY_WAREHOUSES, ALL_ROLES)
def list_warehouses() -> None:
    conn = get_conn()
    table = Table(title="Склады", show_header=True, header_style="bold cyan")

    table.add_column("ID", style="dim", width=6, justify="right")
    table.add_column("Город", style="green", min_width=20)
    table.add_column("Адрес", style="yellow", min_width=30)
    table.add_column("Метка", style="magenta", min_width=15)
    table.add_column("Центральный", style="red", min_width=15)

    with conn.cursor(row_factory=class_row(Warehouse)) as cur:
        cur.execute("SELECT * FROM catalog.warehouses")
        warehouses: list[Warehouse] = cur.fetchall()

    for warehouse in warehouses:
        table.add_row(
            str(warehouse.id),
            get_city_name(warehouse.city_id),
            warehouse.address,
            warehouse.label or "",
            "да" if warehouse.is_central else "нет",
        )
    console.print(table)


@command("show warehouse", "информация о складе", CATEGORY_WAREHOUSES, ALL_ROLES)
def show_warehouse(_id: str) -> None:
    conn = get_conn()
    with conn.cursor(row_factory=class_row(Warehouse)) as cur:
        cur.execute("SELECT * FROM catalog.warehouses WHERE id = %s", (_id,))
        warehouse: Warehouse | None = cur.fetchone()

    if warehouse is None:
        render_error(f"Склад с ID {_id} не найден")
        return

    _render_warehouse(warehouse)


def warehouses_count() -> int:
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM catalog.warehouses")
        count = cur.fetchone()

    return count[0]


def warehouses_empty() -> bool:
    return True if warehouses_count() == 0 else False


@command(
    "add warehouse",
    "добавить склад (интерактивно)",
    CATEGORY_WAREHOUSES,
    [ROLE_CATALOG_MANAGER],
)
def add_warehouse() -> None:
    conn = get_conn()

    cities = get_cities_names()
    city_completer = WordCompleter(cities, ignore_case=True, sentence=True)
    city_validator = ChoiceValidator(
        cities,
        message="Город должен быть из списка. Используйте Tab для автодополнения.",
    )

    city = prompt("Город: ", validator=city_validator, completer=city_completer).strip()
    city_id = get_city_id(city)
    address = prompt("Адрес: ", validator=NonEmptyValidator()).strip()
    label = prompt("Метка (необязательно): ").strip() or None

    if warehouses_empty():
        is_central = True
    else:
        is_central = YesNoValidator.is_yes(
            prompt("Центральный: ", validator=YesNoValidator()).strip()
        )
        if is_central:
            console.log(
                "[yellow bold]Предупреждение:[/bold yellow]: Центральный склад переназначен."
            )
            conn.execute(
                "UPDATE catalog.warehouses SET is_central = FALSE WHERE is_central = TRUE"
            )

    conn.execute(
        "INSERT INTO catalog.warehouses (city_id, address, label, is_central) VALUES (%s, %s, %s, %s)",
        (city_id, address, label, is_central),
    )

    if label:
        console.print(f"[green]Склад в городе {city} ({label}) добавлен [/green]")
    else:
        console.print(f"[green]Склад в городе {city} добавлен [/green]")


@command(
    "edit warehouse", "редактировать склад", CATEGORY_WAREHOUSES, [ROLE_CATALOG_MANAGER]
)
def edit_warehouse(_id: str) -> None:
    conn = get_conn()
    with conn.cursor(row_factory=class_row(Warehouse)) as cur:
        cur.execute("SELECT * FROM catalog.warehouses WHERE id = %s", (_id,))
        warehouse: Warehouse | None = cur.fetchone()

    if warehouse is None:
        render_error(f"Склад с ID {_id} не найден")
        return

    cities = get_cities_names()
    city_completer = WordCompleter(cities, ignore_case=True, sentence=True)
    city_validator = ChoiceValidator(
        cities,
        message="Город должен быть из списка. Используйте Tab для автодополнения.",
    )

    city = prompt(
        "Город: ",
        default=get_city_name(warehouse.city_id),
        validator=city_validator,
        completer=city_completer,
    ).strip()
    city_id = get_city_id(city)
    address = prompt(
        "Адрес: ", default=warehouse.address, validator=NonEmptyValidator()
    ).strip()
    label = (
        prompt("Метка (необязательно): ", default=warehouse.label or "").strip() or None
    )
    if not warehouse.is_central:
        is_central = YesNoValidator.is_yes(
            prompt("Центральный: ", default="нет", validator=YesNoValidator()).strip()
        )
    else:
        is_central = False

    if is_central:
        console.log(
            "[yellow bold]Предупреждение:[/bold yellow]: Центральный склад переназначен"
        )
        conn.execute(
            "UPDATE catalog.warehouses SET is_central = FALSE WHERE is_central = TRUE"
        )

    conn.execute(
        """UPDATE catalog.warehouses SET city_id = %s, address = %s, label = %s, is_central = %s
        WHERE id = %s""",
        (city_id, address, label, is_central, _id),
    )

    if label:
        console.print(f"[green]Склад в городе {city} ({label}) обновлен [/green]")
    else:
        console.print(f"[green]Склад в городе {city} обновлен [/green]")


@command(
    "delete warehouse", "удалить склад", CATEGORY_WAREHOUSES, [ROLE_CATALOG_MANAGER]
)
def delete_warehouse(_id: str) -> None:
    conn = get_conn()
    with conn.cursor(row_factory=class_row(Warehouse)) as cur:
        cur.execute("SELECT * FROM catalog.warehouses WHERE id = %s", (_id,))
        warehouse: Warehouse | None = cur.fetchone()

    if warehouse is None:
        render_error(f"Склад с ID {_id} не найден")
        return

    _render_warehouse(warehouse)
    if warehouse.is_central and warehouses_count() > 1:
        render_error(
            f"Этот склад является центральным, если вы хотите удалить его,"
            f" сначала назначьте другой центральный склад"
        )
        return

    answer = prompt("Вы уверены? (y/n, д/н): ", validator=YesNoValidator())

    if YesNoValidator.is_yes(answer):
        conn.execute("DELETE FROM catalog.warehouses WHERE id = %s", (_id,))

        if warehouse.label:
            console.print(
                f"[green]Склад в городе {get_city_name(warehouse.city_id)} "
                f"({warehouse.label}) удален [/green]"
            )
        else:
            console.print(
                f"[green]Склад в городе {get_city_name(warehouse.city_id)} удален [/green]"
            )


@command(
    "delete all warehouses",
    "удалить все категории товаров",
    CATEGORY_WAREHOUSES,
    [ROLE_CATALOG_MANAGER],
)
def delete_all_warehouses() -> None:
    conn = get_conn()

    count = warehouses_count()

    answer = prompt(
        f"Вы собираетесь удалить {count} складов. Вы уверены? (y/n, д/н): ",
        validator=YesNoValidator(),
    )

    if YesNoValidator.is_yes(answer):
        conn.execute("TRUNCATE TABLE catalog.warehouses")
        console.print(f"[green]Все склады удалены [/green]")
