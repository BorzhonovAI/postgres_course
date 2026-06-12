from prompt_toolkit import prompt
from prompt_toolkit.shortcuts import choice
from psycopg.rows import class_row
from rich.panel import Panel
from rich.table import Table

from commands import command, CATEGORY_PRODUCTS
from console import console, render_error
from db import get_conn
from product_categories import get_product_categories, get_category_name_by_id
from structures import Product
from validators import NonEmptyValidator, YesNoValidator, PriceValidator


def get_product_name_by_id(_id: int) -> str:
    conn = get_conn()
    with conn.cursor(row_factory=class_row(Product)) as cur:
        cur.execute("SELECT * FROM catalog.products WHERE id = %s", (_id,))
        product: Product | None = cur.fetchone()

    return product.name


def get_products_names() -> list[str]:
    conn = get_conn()
    with conn.cursor(row_factory=class_row(Product)) as cur:
        cur.execute("SELECT * FROM catalog.products")
        products: list[Product] = cur.fetchall()

    names_list: list[str] = []
    for product in products:
        names_list.append(product.name)

    return names_list


def get_products() -> list[Product]:
    conn = get_conn()
    with conn.cursor(row_factory=class_row(Product)) as cur:
        cur.execute("SELECT * FROM catalog.products")
        products: list[Product] = cur.fetchall()

    return products


def get_product_by_name(name: str) -> Product | None:
    conn = get_conn()
    with conn.cursor(row_factory=class_row(Product)) as cur:
        cur.execute("SELECT * FROM catalog.products WHERE name = %s", (name,))
        product: Product | None = cur.fetchone()

    return product


def get_product_by_sku(sku: str) -> Product | None:
    conn = get_conn()
    with conn.cursor(row_factory=class_row(Product)) as cur:
        cur.execute("SELECT * FROM catalog.products WHERE sku = %s", (sku,))
        product: Product | None = cur.fetchone()

    return product


def get_product_by_id(_id: int) -> Product | None:
    conn = get_conn()
    with conn.cursor(row_factory=class_row(Product)) as cur:
        cur.execute("SELECT * FROM catalog.products WHERE id = %s", (_id,))
        product: Product | None = cur.fetchone()

    return product


def _render_product(product: Product):  # pylint: disable=unused-argument
    table = Table(show_header=False, box=None, padding=(0, 2))

    table.add_column("Поле", style="bold cyan", width=15)
    table.add_column("Значение", style="white")

    table.add_row("ID", str(product.id))
    table.add_row("SKU", product.sku)
    table.add_row("Имя", product.name)
    table.add_row("Цена", str(product.price))
    table.add_row("Категория", get_category_name_by_id(product.category_id))

    panel = Panel(
        table,
        expand=False,
        title=f"[bold green]Продукт #{product.id}[/bold green]",
        border_style="green",
    )

    console.print(panel)


@command("list products", "список всех товаров", CATEGORY_PRODUCTS)
def list_products() -> None:
    conn = get_conn()
    table = Table(title="Продукты", show_header=True, header_style="bold cyan")

    table.add_column("ID", style="dim", width=6, justify="right")
    table.add_column("SKU", style="green", min_width=20)
    table.add_column("Имя", style="yellow", min_width=30)
    table.add_column("Цена", style="magenta", min_width=15)
    table.add_column("Категория", style="red", min_width=15)

    with conn.cursor(row_factory=class_row(Product)) as cur:
        cur.execute("SELECT * FROM catalog.products")
        products: list[Product] = cur.fetchall()

    for product in products:
        table.add_row(
            str(product.id),
            product.sku,
            product.name,
            str(product.price),
            get_category_name_by_id(product.category_id),
        )
    console.print(table)


@command("show product", "информация о товаре", CATEGORY_PRODUCTS)
def show_product(_id: str) -> None:
    conn = get_conn()
    with conn.cursor(row_factory=class_row(Product)) as cur:
        cur.execute("SELECT * FROM catalog.products WHERE id = %s", (_id,))
        product: Product | None = cur.fetchone()

    if product is None:
        render_error(f"Продукт с ID {_id} не найден")
        return

    _render_product(product)


@command("add product", "добавить товар (интерактивно)", CATEGORY_PRODUCTS)
def add_product() -> None:
    conn = get_conn()

    categories = get_product_categories()
    categories_options = [(cat.id, cat.name) for cat in categories]

    sku = prompt("SKU: ", validator=NonEmptyValidator()).strip()
    name = prompt("Имя: ", validator=NonEmptyValidator()).strip()
    price = prompt("Цена: ", validator=PriceValidator()).strip()
    category_id = choice(
        message="Выберите категорию товара:",
        options=categories_options
    )

    conn.execute(
        "INSERT INTO catalog.products (sku, name, price, category_id) VALUES (%s,%s,%s,%s)",
        (sku, name, price, category_id),
    )

    with conn.cursor(row_factory=class_row(Product)) as cur:
        cur.execute("SELECT * FROM catalog.products WHERE sku = %s", (sku,))
        product: Product | None = cur.fetchone()

    console.print(f"[green]Товар {name} ({product.id}) добавлен [/green]")


@command("edit product", "редактировать товар", CATEGORY_PRODUCTS)
def edit_product(_id: str) -> None:
    conn = get_conn()
    with conn.cursor(row_factory=class_row(Product)) as cur:
        cur.execute("SELECT * FROM catalog.products WHERE id = %s", (_id,))
        product: Product | None = cur.fetchone()

    if product is None:
        render_error(f"Продукт с ID {_id} не найден")
        return

    categories = get_product_categories()
    categories_options = [(cat.id, cat.name) for cat in categories]

    sku = prompt(
        "SKU: ", default=product.sku, validator=NonEmptyValidator()
    ).strip()
    name = prompt(
        "Имя: ", default=product.name, validator=NonEmptyValidator()
    ).strip()
    price = prompt(
        "Цена: ", default=str(product.price), validator=PriceValidator()
    ).strip()
    category_id = choice(
        message="Выберите категорию товара:",
        options=categories_options,
        default=product.category_id,
    )

    conn.execute(
        """UPDATE catalog.products SET sku = %s, name = %s, price = %s, category_id = %s
        WHERE id = %s""",
        (sku, name, price, category_id, _id),
    )

    console.print(f"[green]Продукт ({name}) обновлен [/green]")


@command("delete product", "удалить товар", CATEGORY_PRODUCTS)
def delete_product(_id: str) -> None:
    conn = get_conn()
    with conn.cursor(row_factory=class_row(Product)) as cur:
        cur.execute("SELECT * FROM catalog.products WHERE id = %s", (_id,))
        product: Product | None = cur.fetchone()

    if product is None:
        render_error(f"Продукт с ID {_id} не найден")
        return

    _render_product(product)

    answer = prompt("Вы уверены? (y/n, д/н): ", validator=YesNoValidator())

    if YesNoValidator.is_yes(answer):
        try:
            conn.execute("DELETE FROM catalog.products WHERE id = %s", (_id,))
        except Exception:
            render_error(f"Продукт с ID {_id} не может быть удалён пока на него есть заказ")
            return

        console.print(f"[green]Продукт {product.name} удален [/green]")


def products_count() -> int:
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM catalog.products")
        count = cur.fetchone()

    return count[0]


@command("delete all products", "удалить все товары", CATEGORY_PRODUCTS)
def delete_all_products() -> None:
    conn = get_conn()

    count = products_count()
    answer = (prompt
        (
        f"Вы собираетесь удалить {count} товаров. Вы уверены? (y/n, д/н): ",
        validator=YesNoValidator()
    ))

    if YesNoValidator.is_yes(answer):
        conn.execute("TRUNCATE TABLE catalog.products")
        console.print(f"[green]Все товары удалены [/green]")
