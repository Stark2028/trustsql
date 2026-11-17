from uuid import uuid4

import pytest

from trustsql.catalog import snapshot
from trustsql.errors import TrustSQLError
from trustsql.inspection import change_impact, enforce_semantics, inspect_query
from trustsql.models import Plan
from trustsql.planner import net_sql
from trustsql.policy import validate_sql


def test_net_revenue_lineage_crosses_ctes_and_keeps_filter_dependencies():
    report = inspect_query(validate_sql(net_sql("2026-10-01", "2026-11-01")), snapshot())
    assert report["columns"][0]["sources"] == [
        "order_items.quantity",
        "order_items.unit_price_cents",
        "refunds.amount_cents",
    ]
    assert "orders.order_date" in report["query_dependencies"]
    assert not report["risks"]
    assert change_impact(report, "refunds", "amount_cents")["affected_outputs"] == ["net_revenue_cents"]
    assert change_impact(report, "orders", "order_date")["row_selection_or_join_dependency"]
    assert not change_impact(report, "customers", "region")["referenced_by_query"]


@pytest.mark.parametrize("table", ["payments", "refunds"])
def test_raw_one_to_many_money_joins_are_blocked(table):
    sql = f"SELECT SUM(i.quantity*i.unit_price_cents) AS total FROM order_items i JOIN {table} r ON r.order_id=i.order_id"
    report = inspect_query(validate_sql(sql), snapshot())
    assert report["risks"][0]["code"] == "join_fanout"
    with pytest.raises(TrustSQLError) as raised:
        enforce_semantics(report)
    assert raised.value.code == "semantic_risk"


def test_unknown_column_is_not_fabricated():
    with pytest.raises(TrustSQLError) as raised:
        inspect_query(validate_sql("SELECT invented FROM orders"), snapshot())
    assert raised.value.code == "schema_validation_failed"


def test_star_expands_to_real_columns():
    report = inspect_query(validate_sql("SELECT * FROM products"), snapshot())
    assert {c["output"] for c in report["columns"]} == {"id", "name", "category"}


def test_inspection_api_never_executes_warehouse(client, app, monkeypatch):
    def forbidden(*_):
        raise AssertionError("Inspection must not execute SQL")

    monkeypatch.setattr(app.state.service.warehouse, "execute", forbidden)
    response = client.post(
        "/api/inspect",
        json={
            "sql": "SELECT SUM(amount_cents) AS total FROM refunds",
            "changed_table": "refunds",
            "changed_column": "amount_cents",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["executed"] is False
    assert response.json()["impact"]["affected_outputs"] == ["total"]
    assert client.post("/api/inspect", json={"sql": "DELETE FROM orders"}).status_code == 422
    assert (
        client.post(
            "/api/inspect",
            json={"sql": "SELECT * FROM orders", "changed_table": "orders", "changed_column": "bad"},
        ).status_code
        == 422
    )


def test_query_service_blocks_risky_join_before_execution(app, monkeypatch):
    class Risky:
        def plan(self, _question, evidence):
            return Plan(
                status="answer",
                sql="SELECT SUM(i.quantity*i.unit_price_cents) AS total FROM order_items i JOIN refunds r ON r.order_id=i.order_id",
                explanation="Unsafe grain",
                citations=[d.urn for d in evidence],
            )

    app.state.service.planner = Risky()
    monkeypatch.setattr(app.state.service.warehouse, "execute", lambda *_: pytest.fail("Must not execute"))
    with pytest.raises(TrustSQLError) as raised:
        app.state.service.answer("Net revenue last month", str(uuid4()), "test")
    assert raised.value.code == "semantic_risk"
    assert app.state.service.control.recent()[0]["error_code"] == "semantic_risk"
