from dataclasses import dataclass

from prompt_toolkit import prompt
from psycopg.rows import class_row
from rich.panel import Panel
from rich.table import Table

from console import console, render_error
from db import get_conn
from validators import NonEmptyValidator, YesNoValidator
from commands import command, CATEGORY_PRODUCTS_CATEGORIES


@dataclass
class ProductCategory:
    id: int
    name: str


def _render_product_category(category: ProductCategory) -> None:
    table = Table(show_header=False, box=None, padding=(0, 2))

    table.add_column("Поле", style="bold cyan", width=15)
    table.add_column("Значение", style="white")

    table.add_row("ID", str(category.id))
    table.add_row("Имя", category.name)

    panel = Panel(
        table,
        expand=False,
        title=f"[bold green]Категория товара #{category.id}[/bold green]",
        border_style="green",
    )

    console.print(panel)


@command("list product_categories", "список всех категорий товаров", CATEGORY_PRODUCTS_CATEGORIES)
def list_categories() -> None:
    conn = get_conn()
    table = Table(title="Категории товаров", show_header=True, header_style="bold cyan")

    table.add_column("ID", style="dim", width=6, justify="right")
    table.add_column("Имя", style="green", min_width=20)

    with conn.cursor(row_factory=class_row(ProductCategory)) as cur:
        cur.execute("SELECT * FROM catalog.product_categories")
        categories: list[ProductCategory] = cur.fetchall()

    for category in categories:
        table.add_row(
            str(category.id),
            category.name
        )
    console.print(table)


@command("show product_category", "информация о категории товара", CATEGORY_PRODUCTS_CATEGORIES)
def show_category(_id: str) -> None:
    conn = get_conn()
    with conn.cursor(row_factory=class_row(ProductCategory)) as cur:
        cur.execute("SELECT * FROM catalog.product_categories WHERE id = %s", (_id,))
        category: ProductCategory | None = cur.fetchone()

    if category is None:
        render_error(f"Категория товара с ID {_id} не найдена")
        return

    _render_product_category(category)


# serial даже после удаления элемента не уменьшается
@command("add product_category", "добавить категорию товара (интерактивно)", CATEGORY_PRODUCTS_CATEGORIES)
def add_category() -> None:
    conn = get_conn()
    name = prompt("Имя: ", validator=NonEmptyValidator()).strip()
    conn.execute(
        "INSERT INTO catalog.product_categories (name) VALUES (%s)",
        (name,),  # fucking python
    )

    with conn.cursor(row_factory=class_row(ProductCategory)) as cur:
        cur.execute("SELECT * FROM catalog.product_categories WHERE name = %s", (name,))
        category: ProductCategory | None = cur.fetchone()

    console.print(f"[green]Категория {name} ({category.id}) добавлена [/green]")


@command("edit product_category", "редактировать категорию товара", CATEGORY_PRODUCTS_CATEGORIES)
def edit_category(_id: str) -> None:
    conn = get_conn()
    with conn.cursor(row_factory=class_row(ProductCategory)) as cur:
        cur.execute("SELECT * FROM catalog.product_categories WHERE id = %s", (_id,))
        category: ProductCategory | None = cur.fetchone()

    if category is None:
        render_error(f"Категория товара с ID {_id} не найдена")
        return

    name = prompt(
        "Имя: ", default=category.name, validator=NonEmptyValidator()
    ).strip()

    conn.execute(
        """UPDATE catalog.product_categories SET name = %s
        WHERE id = %s""",
        (name, _id),
    )
    console.print(f"[green]Категория товара обновлена [/green]")


@command("delete product_category", "удалить категорию товара", CATEGORY_PRODUCTS_CATEGORIES)
def delete_category(_id: str) -> None:
    from products import products_count_by_category_id

    conn = get_conn()

    with conn.cursor(row_factory=class_row(ProductCategory)) as cur:
        cur.execute("SELECT * FROM catalog.product_categories WHERE id = %s", (_id,))
        category: ProductCategory | None = cur.fetchone()

    if category is None:
        render_error(f"Категория товара с ID {_id} не найдена")
        return

    _render_product_category(category)

    p_count = products_count_by_category_id(category.id)
    console.log(f"[red bold]Предупреждение:[/bold red]: При удалении категории будет удалено "
                f"{p_count} товаров этой категории")
    answer = prompt("Вы уверены? (y/n, д/н): ", validator=YesNoValidator())

    if YesNoValidator.is_yes(answer):
        conn.execute("DELETE FROM catalog.product_categories WHERE id = %s", (_id,))
        conn.execute("DELETE FROM catalog.products WHERE category_id = %s", (_id,))
        console.print(f"[green]Категория товара удалена [/green]")


def product_categories_count() -> int:
    conn = get_conn()
    with conn.cursor(row_factory=class_row(ProductCategory)) as cur:
        cur.execute("SELECT * FROM catalog.product_categories")
        product_categories: list[ProductCategory] = cur.fetchall()

    return len(product_categories)


def get_product_categories_names() -> list[str]:
    conn = get_conn()
    with conn.cursor(row_factory=class_row(ProductCategory)) as cur:
        cur.execute("SELECT * FROM catalog.product_categories")
        product_categories: list[ProductCategory] = cur.fetchall()

    names_list: list[str] = []
    for category in product_categories:
        names_list.append(category.name)

    return names_list


@command("delete all product_categories", "удалить все категории товаров", CATEGORY_PRODUCTS_CATEGORIES)
def delete_all_product_categories() -> None:
    conn = get_conn()

    count = product_categories_count()

    console.log(f"[red bold]Предупреждение:[/bold red]: При удалении всех "
                f"категорий товаров будут удалены так же и все товары")
    answer = (prompt
        (
        f"Вы собираетесь удалить {count} категорий товаров. Вы уверены? (y/n, д/н): ",
        validator=YesNoValidator()
    ))

    if YesNoValidator.is_yes(answer):
        conn.execute("TRUNCATE TABLE catalog.products")
        conn.execute("TRUNCATE TABLE catalog.product_categories")
        console.print(f"[green]Все категории товаров удалены [/green]")
