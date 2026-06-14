from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime


@dataclass
class OrderItem:
    order_id: int
    product_id: int
    quantity: int
    price: Decimal


@dataclass
class Order:
    id: int
    status: str
    total_amount: Decimal
    created_at: datetime
    warehouse_id: int


@dataclass
class ProductCategory:
    id: int
    name: str


@dataclass
class Product:
    id: int
    sku: str
    name: str
    price: Decimal
    category_id: int


@dataclass
class Warehouse:
    id: int
    city: str
    address: str
    label: str | None
    is_central: bool
