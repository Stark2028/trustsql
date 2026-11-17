import json
import tempfile
import time
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path

from trustsql.catalog import Catalog
from trustsql.config import Settings
from trustsql.db import make_engine
from trustsql.errors import TrustSQLError
from trustsql.inspection import enforce_semantics, inspect_query
from trustsql.models import Dataset
from trustsql.planner import DemoPlanner, LLMPlanner
from trustsql.policy import validate_sql
from trustsql.seed import python_reference, seed_warehouse
from trustsql.warehouse import Warehouse

CASES = [
    {
        "id": "net-revenue",
        "question": "What was our net revenue last month?",
        "expected": "answer",
        "metric": "net_revenue_cents",
        "split": "development",
    },
    {
        "id": "gross-revenue",
        "question": "What was gross revenue last month?",
        "expected": "answer",
        "metric": "gross_revenue_cents",
        "split": "development",
    },
    {
        "id": "completed-orders",
        "question": "How many completed orders were there last month?",
        "expected": "answer",
        "metric": "completed_orders",
        "split": "development",
    },
    {
        "id": "refunds",
        "question": "Show successful refunds for last month",
        "expected": "answer",
        "metric": "refunds_cents",
        "split": "development",
    },
    {
        "id": "ambiguous-revenue",
        "question": "What was revenue last month?",
        "expected": "clarification",
        "split": "development",
    },
    {
        "id": "write-refusal",
        "question": "Delete all cancelled orders",
        "expected": "refusal",
        "split": "development",
    },
]


def run_evaluation(
    settings: Settings,
    output: Path,
    seed_values=(7, 19, 42),
    variant="metadata",
    client=None,
    suite="development",
):
    """Small development suite; never label this prompt-development set held out."""
    if settings.as_of_date.isoformat() != "2026-11-15":
        raise ValueError("The v1 benchmark requires reference date 2026-11-15.")
    if settings.mode == "demo" and variant != "metadata":
        raise ValueError(
            "Schema-only is a live-model experiment, not a meaningful deterministic-demo comparison."
        )
    if suite not in {"development", "expanded"}:
        raise ValueError("Unknown evaluation suite")
    cases = (
        CASES
        if suite == "development"
        else json.loads(
            files("trustsql").joinpath("fixtures/evaluation-expanded.json").read_text(encoding="utf-8")
        )
    )
    catalog = Catalog(settings)
    planner = DemoPlanner(settings) if settings.mode == "demo" else LLMPlanner(settings, client)
    results = []
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix="trustsql-eval-", dir=output.parent) as directory:
            for seed in seed_values:
                engine = make_engine(f"sqlite:///{Path(directory) / f'warehouse-{seed}.db'}")
                try:
                    seed_warehouse(engine, seed)
                    executor = Warehouse(engine, settings)
                    for case in cases:
                        started = time.monotonic()
                        outcome = {
                            "id": case["id"],
                            "seed": seed,
                            "question": case["question"],
                            "split": case["split"],
                            "passed": False,
                        }
                        try:
                            context = catalog.retrieve(case["question"])
                            if variant == "schema_only":
                                context = [
                                    Dataset(
                                        table=d.table,
                                        urn=d.urn,
                                        description="",
                                        columns=[c.model_copy(update={"description": ""}) for c in d.columns],
                                        source=d.source,
                                    )
                                    for d in context
                                ]
                            plan = planner.plan(case["question"], context)
                            outcome["observed_status"] = plan.status
                            outcome["passed"] = plan.status == case["expected"]
                            if plan.status == "answer":
                                # Generation is PostgreSQL in live mode; transpile the approved tree to SQLite for fixture execution.
                                import sqlglot

                                approved = validate_sql(
                                    plan.sql or "", "postgres" if settings.mode == "live" else "sqlite"
                                )
                                provided = {d.urn: d.table for d in context}
                                cited = {provided[u] for u in plan.citations if u in provided}
                                if not set(plan.citations).issubset(provided) or not set(
                                    approved.tables
                                ).issubset(cited):
                                    raise TrustSQLError(
                                        "invalid_evidence", "Missing or unknown dataset citation", 422
                                    )
                                sqlite_sql = sqlglot.transpile(
                                    approved.sql,
                                    read="postgres" if settings.mode == "live" else "sqlite",
                                    write="sqlite",
                                )[0]
                                enforce_semantics(
                                    inspect_query(
                                        approved, context, "postgres" if settings.mode == "live" else "sqlite"
                                    )
                                )
                                columns, rows, _ = executor.execute(validate_sql(sqlite_sql, "sqlite"))
                                if "metric" in case:
                                    reference = python_reference(seed)[case["metric"]]
                                    actual = (
                                        rows
                                        if isinstance(reference, list)
                                        else rows[0][0]
                                        if len(rows) == 1 and len(columns) == 1
                                        else None
                                    )
                                    outcome.update(expected_value=reference, actual_value=actual)
                                    outcome["passed"] = outcome["passed"] and actual == reference
                        except (TrustSQLError, ValueError) as exc:
                            outcome["passed"] = False
                            outcome["error_code"] = (
                                exc.code if isinstance(exc, TrustSQLError) else "evaluation_error"
                            )
                        outcome["duration_ms"] = int((time.monotonic() - started) * 1000)
                        results.append(outcome)
                finally:
                    engine.dispose()
    finally:
        catalog.close()
        if hasattr(planner, "close"):
            planner.close()
    summary = {
        "state": "complete",
        "mode": settings.mode,
        "variant": variant,
        "suite": suite,
        "distinct_questions": len(cases),
        "model": settings.llm_model if settings.mode == "live" else "deterministic-demo",
        "metadata_source": "datahub" if settings.mode == "live" else "snapshot",
        "generated_at": datetime.now(UTC).isoformat(),
        "label": "Deterministic fixture checks; not LLM accuracy"
        if settings.mode == "demo"
        else "Development-set model evaluation; not a held-out benchmark",
        "cases": len(results),
        "passed": sum(r["passed"] for r in results),
        "results": results,
    }
    temporary = output.with_suffix(".tmp")
    temporary.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    temporary.replace(output)
    return summary
