import json
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from trustsql.app import EXAMPLES
from trustsql.control import ControlStore
from trustsql.db import make_engine
from trustsql.errors import TrustSQLError
from trustsql.models import Plan
from trustsql.policy import validate_sql
from trustsql.seed import python_reference, seed_warehouse
from trustsql.warehouse import Warehouse


def test_postgres_numeric_money_keeps_exact_integer_units():
    assert Warehouse._json_value(Decimal("49682520")) == 49682520
    assert Warehouse._json_value(Decimal("1.25")) == "1.25"


@pytest.mark.parametrize("seed", [7, 19, 42])
def test_net_revenue_matches_independent_python_oracle(tmp_path, settings, seed):
    from trustsql.planner import net_sql

    engine = make_engine(f"sqlite:///{tmp_path / f'{seed}.db'}")
    try:
        seed_warehouse(engine, seed)
        warehouse = Warehouse(engine, settings)
        _, rows, _ = warehouse.execute(validate_sql(net_sql("2026-10-01", "2026-11-01"), "sqlite"))
        assert rows == [[python_reference(seed)["net_revenue_cents"]]]
    finally:
        engine.dispose()


@pytest.mark.parametrize("question", EXAMPLES)
def test_all_documented_examples_execute(client, question):
    response = client.post("/api/query", json={"question": question})
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "answer", payload
    assert payload["rows"]
    assert payload["mode"] == "demo"
    assert payload["stages"][-1]["name"] == "Audit"


def test_ambiguous_revenue_requests_clarification_without_execution(client):
    response = client.post("/api/query", json={"question": "What was revenue last month?"}).json()
    assert response["status"] == "clarification"
    assert response["sql"] is None and response["rows"] == []
    assert not any(s["name"] == "Execute" for s in response["stages"])


def test_unsupported_period_is_not_silently_reinterpreted(client):
    response = client.post("/api/query", json={"question": "What was net revenue in March?"}).json()
    assert response["status"] == "clarification"


def test_refusal_is_audited(client):
    response = client.post("/api/query", json={"question": "Delete all orders"}).json()
    assert response["status"] == "refusal"
    assert client.get("/api/runs").json()["runs"][0]["status"] == "refusal"


def test_results_are_capped(app, settings):
    warehouse = Warehouse(app.state.service.warehouse.engine, settings.model_copy(update={"max_rows": 5}))
    columns, rows, truncated = warehouse.execute(validate_sql("SELECT * FROM order_items", "sqlite"))
    assert columns and len(rows) == 5 and truncated


def test_warehouse_normalizes_only_physical_cte_tables(app):
    sql = "WITH orders AS (SELECT id FROM analytics.customers) SELECT * FROM orders"
    columns, rows, _ = app.state.service.warehouse.execute(validate_sql(sql, "sqlite"))
    assert columns == ["id"] and len(rows) == 12


def test_history_and_storage_redact_question_sql_and_rows(client, app):
    question = "What was our net revenue last month?"
    answer = client.post("/api/query", json={"question": question}).json()
    history = client.get("/api/runs").json()
    assert question not in json.dumps(history)
    assert answer["sql"] not in json.dumps(history)
    with app.state.service.control.engine.connect() as connection:
        record = connection.execute(select(app.state.service.control.runs)).mappings().one()
        assert len(record["question_hash"]) == 64
        assert len(record["sql_hash"]) == 64
        assert "question" not in record and "sql" not in record and "rows" not in record


def test_injected_model_sql_never_reaches_executor(app):
    class MaliciousPlanner:
        def plan(self, _question, _evidence):
            return Plan(status="answer", sql="DELETE FROM orders", explanation="bad")

    app.state.service.planner = MaliciousPlanner()
    with pytest.raises(TrustSQLError, match="read-only"):
        app.state.service.answer("Show orders last month", str(uuid4()), "test")
    assert app.state.service.control.recent()[0]["error_code"] == "sql_rejected"


def test_unknown_citation_fails_before_sql(app):
    class BadEvidence:
        def plan(self, _question, _evidence):
            return Plan(
                status="answer",
                sql="SELECT COUNT(*) FROM orders",
                explanation="bad",
                citations=["urn:invented"],
            )

    app.state.service.planner = BadEvidence()
    with pytest.raises(TrustSQLError) as raised:
        app.state.service.answer("How many orders last month?", str(uuid4()), "test")
    assert raised.value.code == "invalid_evidence"


def test_audit_unavailable_fails_closed(app):
    with app.state.service.control.engine.begin() as connection:
        app.state.service.control.runs.drop(connection)
    with pytest.raises(TrustSQLError) as raised:
        app.state.service.answer("What was net revenue last month?", str(uuid4()), "test")
    assert raised.value.code == "audit_unavailable"


def test_atomic_rate_limit_with_concurrent_callers(settings):
    engine = make_engine(settings.control_database_url)
    control = ControlStore(engine)
    control.initialize()

    def consume(_):
        try:
            control.consume("same-client", 5, now=1000)
            return True
        except TrustSQLError as exc:
            assert exc.code == "rate_limited"
            return False

    try:
        with ThreadPoolExecutor(max_workers=6) as pool:
            assert sum(pool.map(consume, range(15))) == 5
        control.consume("same-client", 5, now=1060)
    finally:
        engine.dispose()
