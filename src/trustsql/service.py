import threading
import time

from trustsql.catalog import Catalog
from trustsql.config import Settings
from trustsql.control import ControlStore
from trustsql.errors import TrustSQLError
from trustsql.inspection import enforce_semantics, inspect_query
from trustsql.models import Answer, Stage
from trustsql.planner import DemoPlanner, LLMPlanner
from trustsql.policy import validate_sql
from trustsql.warehouse import Warehouse


class QueryService:
    def __init__(
        self, settings: Settings, warehouse: Warehouse, control: ControlStore, catalog: Catalog, planner=None
    ):
        self.settings = settings
        self.warehouse = warehouse
        self.control = control
        self.catalog = catalog
        self.planner = planner or (DemoPlanner(settings) if settings.mode == "demo" else LLMPlanner(settings))
        self.slots = threading.BoundedSemaphore(settings.max_concurrent_queries)

    def answer(self, question: str, request_id: str, rate_key: str) -> Answer:
        self.control.consume(rate_key, self.settings.rate_limit_per_minute)
        if not self.slots.acquire(blocking=False):
            raise TrustSQLError(
                "busy", "The analyst is at capacity. Retry after a running query completes.", 503
            )
        started = time.monotonic()
        sql, tables, evidence = None, [], []
        try:
            evidence = self.catalog.retrieve(question)
            stages = [
                Stage(
                    name="Retrieve context",
                    status="complete",
                    detail=f"{len(evidence)} datasets from {'DataHub' if self.settings.mode == 'live' else 'the versioned demo snapshot'}",
                )
            ]
            plan = self.planner.plan(question, evidence)
            stages.append(Stage(name="Plan query", status="complete", detail="Structured plan validated"))
            sql = plan.sql
            known_urns = {d.urn for d in evidence}
            if not set(plan.citations).issubset(known_urns):
                raise TrustSQLError(
                    "invalid_evidence",
                    "The model cited metadata that was not retrieved. No query was executed.",
                    422,
                )
            columns, rows, truncated = [], [], False
            inspection = None
            if plan.status == "answer":
                approved = validate_sql(sql or "", self.warehouse.dialect)
                tables = list(approved.tables)
                provided = {d.table for d in evidence}
                cited = {d.table for d in evidence if d.urn in plan.citations}
                if not set(tables).issubset(provided & cited):
                    raise TrustSQLError(
                        "invalid_evidence",
                        "The query uses a dataset without retrieved and cited metadata. No query was executed.",
                        422,
                    )
                stages.append(
                    Stage(
                        name="Validate SQL",
                        status="complete",
                        detail="Read query, approved tables and functions",
                    )
                )
                inspection = inspect_query(approved, evidence, self.warehouse.dialect)
                enforce_semantics(inspection)
                stages.append(
                    Stage(
                        name="Inspect semantics",
                        status="complete",
                        detail="Column schema resolved; commerce join-grain checks passed",
                    )
                )
                if not self.warehouse.ready():
                    raise TrustSQLError(
                        "warehouse_not_ready",
                        "The warehouse is not ready or its reader privileges do not satisfy the execution policy.",
                        503,
                    )
                columns, rows, truncated = self.warehouse.execute(approved)
                stages.append(
                    Stage(
                        name="Execute", status="complete", detail=f"{len(rows)} rows under read-only controls"
                    )
                )
                evidence = [d for d in evidence if d.table in tables]
            warnings = []
            if self.settings.mode == "demo":
                warnings.append(
                    "Deterministic demo on synthetic data. This run does not call an LLM or DataHub."
                )
            if any(d.freshness in {"unknown", "stale"} for d in evidence):
                warnings.append(
                    "Freshness is unknown or stale for a selected dataset. Verify it before using this result."
                )
            if truncated:
                warnings.append(f"Results were limited to {self.settings.max_rows} rows.")
            elapsed = int((time.monotonic() - started) * 1000)
            self.control.record(
                request_id=request_id,
                question=question,
                sql=sql,
                mode=self.settings.mode,
                status=plan.status,
                duration_ms=elapsed,
                tables=tables,
                metadata_source="datahub" if self.settings.mode == "live" else "snapshot",
            )
            stages.append(Stage(name="Audit", status="complete", detail="Redacted run record persisted"))
            return Answer(
                request_id=request_id,
                status=plan.status,
                mode=self.settings.mode,
                explanation=plan.explanation,
                sql=sql,
                columns=columns,
                rows=rows,
                row_count=len(rows),
                truncated=truncated,
                evidence=evidence,
                warnings=warnings,
                stages=stages,
                duration_ms=elapsed,
                inspection=inspection,
            )
        except TrustSQLError as exc:
            if exc.code != "audit_unavailable":
                self.control.record(
                    request_id=request_id,
                    question=question,
                    sql=sql,
                    mode=self.settings.mode,
                    status="error",
                    duration_ms=int((time.monotonic() - started) * 1000),
                    tables=tables,
                    metadata_source="datahub" if self.settings.mode == "live" else "snapshot",
                    error_code=exc.code,
                )
            raise
        finally:
            self.slots.release()
