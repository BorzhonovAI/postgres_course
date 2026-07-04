import dataclasses
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
import sys

import pytest

# ─── Import structures directly (bypass handlers/__init__.py eager auto-import) ───
# structures.py lives under src/handlers/ and has no DB side-effects. We add
# its directory to sys.path so we can import the module without triggering
# the auto-discovery in handlers/__init__.py (which imports orders.py,
# products.py, etc. — all of which reach for a live DB connection).
_structures_dir = str(Path(__file__).resolve().parent.parent / "src" / "handlers")
if _structures_dir not in sys.path:
    sys.path.insert(0, _structures_dir)

from structures import (  # noqa: E402
    City,
    Delivery,
    DeliveryItem,
    Order,
    OrderItem,
    Product,
    ProductCategory,
    Reserve,
    Route,
    Stock,
    Transfer,
    TransferItem,
    Warehouse,
)


class TestOrderItem:
    """OrderItem maps order_items table rows."""

    def test_is_dataclass(self):
        assert dataclasses.is_dataclass(OrderItem)

    def test_fields(self):
        fields = {f.name: f.type for f in dataclasses.fields(OrderItem)}
        assert fields == {
            "order_id": int,
            "product_id": int,
            "quantity": int,
            "price": Decimal,
        }

    def test_instance(self):
        oi = OrderItem(order_id=1, product_id=42, quantity=3, price=Decimal("9.99"))
        assert oi.order_id == 1
        assert oi.product_id == 42
        assert oi.quantity == 3
        assert oi.price == Decimal("9.99")


class TestOrder:
    """Order maps orders table rows."""

    def test_is_dataclass(self):
        assert dataclasses.is_dataclass(Order)

    def test_fields(self):
        fields = {f.name: f.type for f in dataclasses.fields(Order)}
        assert fields == {
            "id": int,
            "status": str,
            "total_amount": Decimal,
            "created_at": datetime,
            "warehouse_id": int,
            "created_by_id": int,
            "processing_by": int | None,
        }

    def test_processing_by_defaults_to_none(self):
        now = datetime(2025, 6, 1, 12, 0)
        order = Order(
            id=1,
            status="new",
            total_amount=Decimal("50.0"),
            created_at=now,
            warehouse_id=1,
            created_by_id=2,
        )
        assert order.processing_by is None

    def test_processing_by_set(self):
        now = datetime(2025, 6, 1, 12, 0)
        order = Order(
            id=2,
            status="processing",
            total_amount=Decimal("10.0"),
            created_at=now,
            warehouse_id=1,
            created_by_id=2,
            processing_by=5,
        )
        assert order.processing_by == 5


class TestProductCategory:
    """ProductCategory maps product_categories table rows."""

    def test_is_dataclass(self):
        assert dataclasses.is_dataclass(ProductCategory)

    def test_fields(self):
        fields = {f.name: f.type for f in dataclasses.fields(ProductCategory)}
        assert fields == {"id": int, "name": str}

    def test_instance(self):
        pc = ProductCategory(id=1, name="Electronics")
        assert pc.id == 1
        assert pc.name == "Electronics"


class TestProduct:
    """Product maps products table rows."""

    def test_is_dataclass(self):
        assert dataclasses.is_dataclass(Product)

    def test_fields(self):
        fields = {f.name: f.type for f in dataclasses.fields(Product)}
        assert fields == {
            "id": int,
            "sku": str,
            "name": str,
            "price": Decimal,
            "category_id": int,
        }

    def test_instance(self):
        p = Product(
            id=1, sku="ABC-001", name="Widget", price=Decimal("1.23"), category_id=2
        )
        assert p.sku == "ABC-001"
        assert p.price == Decimal("1.23")


class TestWarehouse:
    """Warehouse maps warehouses table rows."""

    def test_is_dataclass(self):
        assert dataclasses.is_dataclass(Warehouse)

    def test_fields(self):
        fields = {f.name: f.type for f in dataclasses.fields(Warehouse)}
        assert fields == {
            "id": int,
            "city_id": int,
            "address": str,
            "label": str | None,
            "is_central": bool,
        }

    def test_label_omitted_is_none(self):
        # label: str | None — Python 3.10 dataclasses require explicit None
        w = Warehouse(id=1, city_id=1, address="Main St", label=None, is_central=True)
        assert w.label is None

    def test_label_set(self):
        w = Warehouse(
            id=2, city_id=1, address="Side St", label="WH-2", is_central=False
        )
        assert w.label == "WH-2"


class TestCity:
    """City maps cities table rows."""

    def test_is_dataclass(self):
        assert dataclasses.is_dataclass(City)

    def test_fields(self):
        fields = {f.name: f.type for f in dataclasses.fields(City)}
        assert fields == {"id": int, "name": str}


class TestRoute:
    """Route maps routes table rows."""

    def test_is_dataclass(self):
        assert dataclasses.is_dataclass(Route)

    def test_fields(self):
        fields = {f.name: f.type for f in dataclasses.fields(Route)}
        assert fields == {
            "from_city_id": int,
            "to_city_id": int,
            "duration": timedelta,
            "total_threshold": Decimal,
        }

    def test_instance(self):
        r = Route(
            from_city_id=1,
            to_city_id=2,
            duration=timedelta(hours=3),
            total_threshold=Decimal("10"),
        )
        assert r.duration == timedelta(hours=3)


class TestStock:
    """Stock maps stocks table rows."""

    def test_is_dataclass(self):
        assert dataclasses.is_dataclass(Stock)

    def test_fields(self):
        fields = {f.name: f.type for f in dataclasses.fields(Stock)}
        assert fields == {
            "warehouse_id": int,
            "product_id": int,
            "quantity": int,
        }


class TestDelivery:
    """Delivery maps deliveries table rows."""

    def test_is_dataclass(self):
        assert dataclasses.is_dataclass(Delivery)

    def test_fields(self):
        fields = {f.name: f.type for f in dataclasses.fields(Delivery)}
        assert fields == {
            "order_id": int,
            "status": str,
            "created_at": datetime,
            "shipped_at": datetime | None,
            "created_by": int,
        }

    def test_shipped_at_none(self):
        d = Delivery(
            order_id=5,
            status="planned",
            created_at=datetime(2025, 7, 1),
            shipped_at=None,
            created_by=3,
        )
        assert d.shipped_at is None

    def test_shipped_at_set(self):
        d = Delivery(
            order_id=6,
            status="shipped",
            created_at=datetime(2025, 7, 1),
            shipped_at=datetime(2025, 7, 2),
            created_by=3,
        )
        assert d.shipped_at == datetime(2025, 7, 2)


class TestDeliveryItem:
    """DeliveryItem maps delivery_items table rows."""

    def test_is_dataclass(self):
        assert dataclasses.is_dataclass(DeliveryItem)

    def test_fields(self):
        fields = {f.name: f.type for f in dataclasses.fields(DeliveryItem)}
        assert fields == {
            "order_id": int,
            "product_id": int,
            "quantity": int,
            "status": str,
        }


class TestTransfer:
    """Transfer maps transfers table rows."""

    def test_is_dataclass(self):
        assert dataclasses.is_dataclass(Transfer)

    def test_fields(self):
        fields = {f.name: f.type for f in dataclasses.fields(Transfer)}
        assert fields == {
            "id": int,
            "from_warehouse_id": int,
            "to_warehouse_id": int,
            "status": str,
            "created_at": datetime,
            "started_at": datetime | None,
            "arriving_at": datetime | None,
            "received_at": datetime | None,
        }

    def test_optional_datetime_fields_none(self):
        t = Transfer(
            id=1,
            from_warehouse_id=1,
            to_warehouse_id=2,
            status="in_transit",
            created_at=datetime(2025, 8, 1),
            started_at=None,
            arriving_at=None,
            received_at=None,
        )
        assert t.started_at is None
        assert t.arriving_at is None
        assert t.received_at is None

    def test_optional_datetime_fields_set(self):
        t = Transfer(
            id=2,
            from_warehouse_id=1,
            to_warehouse_id=2,
            status="received",
            created_at=datetime(2025, 8, 1),
            started_at=datetime(2025, 8, 2),
            arriving_at=datetime(2025, 8, 3),
            received_at=datetime(2025, 8, 4),
        )
        assert t.started_at == datetime(2025, 8, 2)
        assert t.arriving_at == datetime(2025, 8, 3)
        assert t.received_at == datetime(2025, 8, 4)


class TestTransferItem:
    """TransferItem maps transfer_items table rows."""

    def test_is_dataclass(self):
        assert dataclasses.is_dataclass(TransferItem)

    def test_fields(self):
        fields = {f.name: f.type for f in dataclasses.fields(TransferItem)}
        assert fields == {
            "id": int,
            "transfer_id": int,
            "product_id": int,
            "quantity": int,
            "requested_by": int,
            "reserve_id": int | None,
            "status": str,
        }

    def test_reserve_id_none(self):
        ti = TransferItem(
            id=1,
            transfer_id=10,
            product_id=5,
            quantity=2,
            requested_by=3,
            reserve_id=None,
            status="planned",
        )
        assert ti.reserve_id is None

    def test_reserve_id_set(self):
        ti = TransferItem(
            id=2,
            transfer_id=10,
            product_id=5,
            quantity=2,
            requested_by=3,
            reserve_id=7,
            status="shipped",
        )
        assert ti.reserve_id == 7


class TestReserve:
    """Reserve maps reserves table rows."""

    def test_is_dataclass(self):
        assert dataclasses.is_dataclass(Reserve)

    def test_fields(self):
        fields = {f.name: f.type for f in dataclasses.fields(Reserve)}
        assert fields == {
            "id": int,
            "order_id": int,
            "product_id": int,
            "quantity": int,
        }


class TestAllStructures:
    """Cross-cutting checks on all dataclasses."""

    ALL = [
        OrderItem,
        Order,
        ProductCategory,
        Product,
        Warehouse,
        City,
        Route,
        Stock,
        Delivery,
        DeliveryItem,
        Transfer,
        TransferItem,
        Reserve,
    ]

    def test_all_are_dataclasses(self):
        for cls in self.ALL:
            assert dataclasses.is_dataclass(cls), f"{cls.__name__} is not a dataclass"

    def test_no_none_default_for_required_fields(self):
        """Non-optional fields must have no default (no risk of silent None)."""
        for cls in self.ALL:
            for field in dataclasses.fields(cls):
                if field.default is not dataclasses.MISSING:
                    # Field has a default — it should be optional type
                    assert (
                        field.default is None
                    ), f"{cls.__name__}.{field.name} has unexpected default {field.default}"
