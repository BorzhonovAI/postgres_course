from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime, timedelta


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
    created_by_id: int
    processing_by: int | None = None


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
    city_id: int
    address: str
    label: str | None
    is_central: bool


@dataclass
class City:
    id: int
    name: str


# ─── Inventory domain ───


@dataclass
class Route:
    from_city_id: int
    to_city_id: int
    duration: timedelta
    total_threshold: Decimal


@dataclass
class Stock:
    warehouse_id: int
    product_id: int
    quantity: int


@dataclass
class Delivery:
    order_id: int
    status: str
    created_at: datetime
    shipped_at: datetime | None
    created_by: int


@dataclass
class DeliveryItem:
    order_id: int
    product_id: int
    quantity: int
    status: str


@dataclass
class Transfer:
    id: int
    from_warehouse_id: int
    to_warehouse_id: int
    status: str
    created_at: datetime
    started_at: datetime | None
    arriving_at: datetime | None
    received_at: datetime | None


@dataclass
class TransferItem:
    id: int
    transfer_id: int
    product_id: int
    quantity: int
    requested_by: int
    reserve_id: int | None
    status: str


@dataclass
class Reserve:
    id: int
    order_id: int
    product_id: int
    quantity: int
