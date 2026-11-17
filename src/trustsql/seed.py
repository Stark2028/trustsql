"""Explicit, idempotent synthetic fixture bootstrap. Never invoked by query execution."""

import random

from sqlalchemy import Column, ForeignKey, Integer, MetaData, String, Table, func, select
from sqlalchemy.engine import Engine

SCHEMA = "analytics"


def warehouse_tables(dialect: str):
    metadata = MetaData(schema=SCHEMA if dialect == "postgresql" else None)
    customers = Table(
        "customers",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("segment", String(30), nullable=False),
        Column("region", String(30), nullable=False),
    )
    products = Table(
        "products",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String(80), nullable=False),
        Column("category", String(30), nullable=False),
    )
    orders = Table(
        "orders",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("customer_id", ForeignKey(customers.c.id), nullable=False),
        Column("order_date", String(10), nullable=False),
        Column("status", String(20), nullable=False),
    )
    items = Table(
        "order_items",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("order_id", ForeignKey(orders.c.id), nullable=False),
        Column("product_id", ForeignKey(products.c.id), nullable=False),
        Column("quantity", Integer, nullable=False),
        Column("unit_price_cents", Integer, nullable=False),
    )
    payments = Table(
        "payments",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("order_id", ForeignKey(orders.c.id), nullable=False),
        Column("amount_cents", Integer, nullable=False),
        Column("status", String(20), nullable=False),
    )
    refunds = Table(
        "refunds",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("order_id", ForeignKey(orders.c.id), nullable=False),
        Column("amount_cents", Integer, nullable=False),
        Column("status", String(20), nullable=False),
    )
    return metadata, {t.name: t for t in [customers, products, orders, items, payments, refunds]}


def fixture_rows(seed: int = 7):
    rng = random.Random(seed)
    customers = [
        {
            "id": i,
            "segment": ["Consumer", "Business", "Enterprise"][(i - 1) % 3],
            "region": ["South", "North", "West", "East"][(i - 1) % 4],
        }
        for i in range(1, 13)
    ]
    products = [
        {"id": i, "name": name, "category": category}
        for i, (name, category) in enumerate(
            [
                ("Mechanical Keyboard", "Accessories"),
                ("Studio Headphones", "Audio"),
                ("USB-C Dock", "Accessories"),
                ("Portable Speaker", "Audio"),
                ("Desk Lamp", "Home"),
                ("Monitor Stand", "Home"),
            ],
            1,
        )
    ]
    orders, items, payments, refunds = [], [], [], []
    for oid in range(1, 61):
        month = 9 if oid <= 10 else 10 if oid <= 50 else 11
        orders.append(
            {
                "id": oid,
                "customer_id": (oid - 1) % 12 + 1,
                "order_date": f"2026-{month:02d}-{(oid * 3) % 27 + 1:02d}",
                "status": "cancelled" if oid % 9 == 0 else "completed",
            }
        )
        total = 0
        for j in range(1 + oid % 3):
            price = rng.choice([149900, 249900, 349900, 499900])
            qty = rng.randint(1, 3)
            items.append(
                {
                    "id": len(items) + 1,
                    "order_id": oid,
                    "product_id": (oid + j) % 6 + 1,
                    "quantity": qty,
                    "unit_price_cents": price,
                }
            )
            total += qty * price
        # Multiple payments deliberately create a join-fanout trap.
        for amount in [total // 2, total - total // 2] if oid % 4 == 0 else [total]:
            payments.append(
                {
                    "id": len(payments) + 1,
                    "order_id": oid,
                    "amount_cents": amount,
                    "status": "captured" if oid % 9 else "void",
                }
            )
        if oid % 5 == 0 and oid % 9:
            for amount in [total // 10, total // 20]:
                refunds.append(
                    {"id": len(refunds) + 1, "order_id": oid, "amount_cents": amount, "status": "succeeded"}
                )
        if oid % 7 == 0:
            refunds.append(
                {"id": len(refunds) + 1, "order_id": oid, "amount_cents": 10000, "status": "pending"}
            )
    return {
        "customers": customers,
        "products": products,
        "orders": orders,
        "order_items": items,
        "payments": payments,
        "refunds": refunds,
    }


def seed_warehouse(engine: Engine, seed: int = 7) -> bool:
    metadata, tables = warehouse_tables(engine.dialect.name)
    metadata.create_all(engine)
    with engine.begin() as connection:
        if connection.scalar(select(func.count()).select_from(tables["orders"])):
            return False
        for name, rows in fixture_rows(seed).items():
            connection.execute(tables[name].insert(), rows)
    return True


def python_reference(seed: int = 7):
    """Independent, non-SQL oracle for the benchmark's aggregate metrics."""
    rows = fixture_rows(seed)
    completed = {
        o["id"]
        for o in rows["orders"]
        if o["status"] == "completed" and "2026-10-01" <= o["order_date"] < "2026-11-01"
    }
    gross = sum(
        i["quantity"] * i["unit_price_cents"] for i in rows["order_items"] if i["order_id"] in completed
    )
    refunded = sum(
        r["amount_cents"]
        for r in rows["refunds"]
        if r["order_id"] in completed and r["status"] == "succeeded"
    )
    result = {
        "gross_revenue_cents": gross,
        "net_revenue_cents": gross - refunded,
        "refunds_cents": refunded,
        "completed_orders": len(completed),
    }
    product_names = {p["id"]: p["name"] for p in rows["products"]}
    customer_segments = {c["id"]: c["segment"] for c in rows["customers"]}
    order_customers = {o["id"]: o["customer_id"] for o in rows["orders"]}
    by_product, by_segment, by_region = {}, {}, {}
    for item in rows["order_items"]:
        if item["order_id"] not in completed:
            continue
        amount = item["quantity"] * item["unit_price_cents"]
        name = product_names[item["product_id"]]
        segment = customer_segments[order_customers[item["order_id"]]]
        by_product[name] = by_product.get(name, 0) + amount
        by_segment[segment] = by_segment.get(segment, 0) + amount
    for customer in rows["customers"]:
        region = customer["region"]
        by_region[region] = by_region.get(region, 0) + 1
    result["top_products"] = [
        list(pair) for pair in sorted(by_product.items(), key=lambda p: (-p[1], p[0]))[:5]
    ]
    result["segment_sales"] = [list(pair) for pair in sorted(by_segment.items(), key=lambda p: (-p[1], p[0]))]
    result["customer_regions"] = [
        list(pair) for pair in sorted(by_region.items(), key=lambda p: (-p[1], p[0]))
    ]
    monthly_orders = {o["id"] for o in rows["orders"] if "2026-10-01" <= o["order_date"] < "2026-11-01"}
    result["captured_payments_cents"] = sum(
        p["amount_cents"]
        for p in rows["payments"]
        if p["order_id"] in monthly_orders and p["status"] == "captured"
    )
    return result
