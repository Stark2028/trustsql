import hashlib
import time
from datetime import UTC, datetime

from sqlalchemy import JSON, Column, Integer, MetaData, String, Table, delete, inspect, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from trustsql.errors import TrustSQLError


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class ControlStore:
    def __init__(self, engine: Engine):
        self.engine = engine
        self.metadata = MetaData(schema="control" if engine.dialect.name == "postgresql" else None)
        self.version = Table(
            "schema_version",
            self.metadata,
            Column("id", Integer, primary_key=True),
            Column("version", Integer, nullable=False),
        )
        self.windows = Table(
            "rate_windows",
            self.metadata,
            Column("key", String(64), primary_key=True),
            Column("window", Integer, primary_key=True),
            Column("count", Integer, nullable=False),
        )
        self.runs = Table(
            "query_runs",
            self.metadata,
            Column("request_id", String(36), primary_key=True),
            Column("created_at", String(40), nullable=False),
            Column("question_hash", String(64), nullable=False),
            Column("sql_hash", String(64)),
            Column("mode", String(12), nullable=False),
            Column("status", String(30), nullable=False),
            Column("duration_ms", Integer, nullable=False),
            Column("tables", JSON, nullable=False),
            Column("metadata_source", String(20), nullable=False),
            Column("error_code", String(50)),
        )

    def initialize(self):
        self.metadata.create_all(self.engine)
        insert = pg_insert if self.engine.dialect.name == "postgresql" else sqlite_insert
        with self.engine.begin() as connection:
            connection.execute(insert(self.version).values(id=1, version=1).on_conflict_do_nothing())
        if not self.ready():
            raise RuntimeError("Unsupported control schema version")

    def ready(self):
        try:
            schema = "control" if self.engine.dialect.name == "postgresql" else None
            if not {"schema_version", "rate_windows", "query_runs"}.issubset(
                set(inspect(self.engine).get_table_names(schema=schema))
            ):
                return False
            with self.engine.connect() as connection:
                return connection.scalar(select(self.version.c.version).where(self.version.c.id == 1)) == 1
        except SQLAlchemyError:
            return False

    def consume(self, key: str, limit: int, now: float | None = None):
        window = int((time.time() if now is None else now) // 60)
        insert = pg_insert if self.engine.dialect.name == "postgresql" else sqlite_insert
        statement = insert(self.windows).values(key=digest(key), window=window, count=1)
        statement = statement.on_conflict_do_update(
            index_elements=[self.windows.c.key, self.windows.c.window],
            set_={"count": self.windows.c.count + 1},
        ).returning(self.windows.c.count)
        try:
            with self.engine.begin() as connection:
                connection.execute(delete(self.windows).where(self.windows.c.window < window - 2))
                count = connection.scalar(statement)
        except SQLAlchemyError as exc:
            raise TrustSQLError(
                "audit_unavailable",
                "The audit database is unavailable. Queries are paused until it recovers.",
                503,
            ) from exc
        if count > limit:
            raise TrustSQLError(
                "rate_limited", "The query limit has been reached. Try again in one minute.", 429
            )

    def record(
        self,
        *,
        request_id: str,
        question: str,
        sql: str | None,
        mode: str,
        status: str,
        duration_ms: int,
        tables: list[str],
        metadata_source: str,
        error_code: str | None = None,
    ):
        try:
            with self.engine.begin() as connection:
                connection.execute(
                    self.runs.insert().values(
                        request_id=request_id,
                        created_at=datetime.now(UTC).isoformat(),
                        question_hash=digest(question),
                        sql_hash=digest(sql) if sql else None,
                        mode=mode,
                        status=status,
                        duration_ms=duration_ms,
                        tables=tables,
                        metadata_source=metadata_source,
                        error_code=error_code,
                    )
                )
        except SQLAlchemyError as exc:
            raise TrustSQLError(
                "audit_unavailable",
                "The run could not be recorded. Results are withheld until the audit database recovers.",
                503,
            ) from exc

    def recent(self):
        try:
            with self.engine.connect() as connection:
                return [
                    dict(r)
                    for r in connection.execute(
                        select(
                            self.runs.c.request_id,
                            self.runs.c.created_at,
                            self.runs.c.mode,
                            self.runs.c.status,
                            self.runs.c.duration_ms,
                            self.runs.c.tables,
                            self.runs.c.metadata_source,
                            self.runs.c.error_code,
                        )
                        .order_by(self.runs.c.created_at.desc())
                        .limit(30)
                    ).mappings()
                ]
        except SQLAlchemyError as exc:
            raise TrustSQLError("audit_unavailable", "Run history is temporarily unavailable.", 503) from exc

    def ping(self):
        with self.engine.connect() as connection:
            return connection.scalar(text("SELECT 1")) == 1
