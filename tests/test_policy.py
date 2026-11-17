import pytest

from trustsql.errors import TrustSQLError
from trustsql.planner import net_sql
from trustsql.policy import validate_sql


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM orders",
        "UPDATE orders SET status='cancelled'",
        "DROP TABLE orders",
        "SELECT * FROM orders; DELETE FROM orders",
        "SELECT * INTO stolen FROM orders",
        "WITH changed AS (DELETE FROM orders RETURNING *) SELECT * FROM changed",
        "SELECT pg_read_file('/etc/passwd') FROM orders",
        "SELECT pg_sleep(10) FROM orders",
        "SELECT set_config('search_path', 'public', false) FROM orders",
        "SELECT * FROM information_schema.tables",
        "SELECT * FROM pg_catalog.pg_authid",
        "SELECT * FROM other.orders",
        "SELECT * FROM another.analytics.orders",
        "SELECT * FROM generate_series(1,100000000)",
        "SELECT * FROM orders FOR UPDATE",
        "WITH RECURSIVE q AS (SELECT * FROM orders UNION ALL SELECT * FROM q) SELECT * FROM q",
        "SELECT load_extension('bad') FROM orders",
        "PRAGMA query_only=OFF",
        "ATTACH DATABASE 'bad' AS bad",
        "SELECT * FROM sqlite_master",
        "SELECT 1",
        "",
        "SELECT * FROM refunds UNION SELECT * FROM unknown",
        "SELECT * FROM orders o CROSS JOIN LATERAL (SELECT * FROM payments) p",
        "SELECT (SELECT pg_sleep(5)) FROM orders",
        "SELECT * FROM read_csv('/tmp/data')",
        "SELECT public.sum(amount_cents) FROM payments",
    ],
)
def test_rejects_unsafe_or_out_of_scope_sql(sql):
    with pytest.raises(TrustSQLError) as raised:
        validate_sql(sql)
    assert raised.value.code == "sql_rejected"


@pytest.mark.parametrize(
    "sql,expected",
    [
        ("SELECT COUNT(*) FROM orders", ("orders",)),
        ("SELECT 'DROP TABLE orders; DELETE FROM orders' AS note FROM orders LIMIT 1", ("orders",)),
        ("SELECT * FROM analytics.orders", ("orders",)),
        (
            "WITH totals AS (SELECT order_id, SUM(amount_cents) AS amount FROM refunds GROUP BY order_id) SELECT * FROM totals",
            ("refunds",),
        ),
        ("SELECT id FROM orders UNION SELECT id FROM customers", ("customers", "orders")),
        (net_sql("2026-10-01", "2026-11-01"), ("order_items", "orders", "refunds")),
    ],
)
def test_approved_queries_have_physical_lineage(sql, expected):
    assert validate_sql(sql).tables == expected
