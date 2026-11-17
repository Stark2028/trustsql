import sqlite3
import time
from datetime import date, datetime
from decimal import Decimal

import sqlglot
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlglot import exp
from sqlglot.optimizer.scope import traverse_scope

from trustsql.config import Settings
from trustsql.errors import TrustSQLError
from trustsql.policy import TABLES, ApprovedQuery


class Warehouse:
    def __init__(self, engine: Engine, settings: Settings):
        self.engine = engine
        self.settings = settings
        self.dialect = "postgres" if engine.dialect.name == "postgresql" else "sqlite"

    def ready(self):
        try:
            schema = "analytics" if self.dialect == "postgres" else None
            if not TABLES.issubset(set(inspect(self.engine).get_table_names(schema=schema))):
                return False
            if self.dialect == "postgres":
                with self.engine.connect() as connection:
                    role = connection.execute(
                        text(
                            "SELECT rolsuper, rolcreaterole, rolcreatedb, rolbypassrls FROM pg_roles WHERE rolname = current_user"
                        )
                    ).one()
                    if any(role):
                        return False
                    if connection.scalar(text("SHOW default_transaction_read_only")) != "on":
                        return False
                    for table in sorted(TABLES):
                        writable = connection.scalar(
                            text(
                                "SELECT has_table_privilege(current_user, :table, 'INSERT,UPDATE,DELETE,TRUNCATE')"
                            ),
                            {"table": f"analytics.{table}"},
                        )
                        if writable:
                            return False
            return True
        except SQLAlchemyError:
            return False

    def execute(self, approved: ApprovedQuery):
        tree = sqlglot.parse_one(approved.sql, read=self.dialect)
        # Only physical sources are qualified. A CTE can legitimately shadow a catalog table name.
        for scope in traverse_scope(tree):
            for source in scope.sources.values():
                if isinstance(source, exp.Table):
                    source.set("db", exp.to_identifier("analytics") if self.dialect == "postgres" else None)
        query = tree.sql(dialect=self.dialect)
        bounded = f"SELECT * FROM ({query}) AS trustsql_result LIMIT {self.settings.max_rows + 1}"
        try:
            if self.dialect == "sqlite":
                columns, rows = self._sqlite(bounded)
            else:
                with self.engine.connect() as connection, connection.begin():
                    connection.execute(text("SET TRANSACTION READ ONLY"))
                    connection.execute(
                        text("SELECT set_config('statement_timeout', :timeout, true)"),
                        {"timeout": str(self.settings.query_timeout_seconds * 1000)},
                    )
                    connection.execute(text("SELECT set_config('lock_timeout', '1000', true)"))
                    result = connection.execute(text(bounded))
                    columns, rows = list(result.keys()), result.fetchmany(self.settings.max_rows + 1)
        except (SQLAlchemyError, sqlite3.Error) as exc:
            raise TrustSQLError(
                "query_execution_failed",
                "The query could not complete within the database policy. Refine the question or inspect the generated SQL.",
                422,
            ) from exc
        truncated = len(rows) > self.settings.max_rows
        return (
            columns,
            [[self._json_value(v) for v in row] for row in rows[: self.settings.max_rows]],
            truncated,
        )

    def _sqlite(self, query):
        deadline = time.monotonic() + self.settings.query_timeout_seconds
        raw = self.engine.raw_connection()
        connection = raw.driver_connection

        def authorizer(action, arg1, arg2, database, _trigger):
            # SQLite's optimized COUNT(*) read reports database=None, column=''.
            if action == sqlite3.SQLITE_READ and (arg1 not in TABLES or database not in {None, "main"}):
                return sqlite3.SQLITE_DENY
            if action not in {
                sqlite3.SQLITE_SELECT,
                sqlite3.SQLITE_READ,
                sqlite3.SQLITE_FUNCTION,
                sqlite3.SQLITE_RECURSIVE,
            }:
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK

        try:
            connection.execute("PRAGMA query_only=ON")
            connection.set_authorizer(authorizer)
            connection.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
            cursor = connection.execute(query)
            columns = [d[0] for d in cursor.description]
            rows = cursor.fetchmany(self.settings.max_rows + 1)
            cursor.close()
            return columns, rows
        finally:
            connection.set_authorizer(None)
            connection.set_progress_handler(None, 0)
            connection.rollback()
            raw.close()

    @staticmethod
    def _json_value(value):
        if isinstance(value, Decimal):
            # PostgreSQL SUM(bigint) returns numeric/Decimal; preserve exact integer cents.
            return int(value) if value.is_finite() and value == value.to_integral_value() else str(value)
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        return value
