"""Non-destructive checks using the application's configured reader/control roles."""

import json

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from trustsql.catalog import Catalog
from trustsql.config import Settings
from trustsql.control import ControlStore
from trustsql.db import make_engine
from trustsql.planner import net_sql
from trustsql.policy import validate_sql
from trustsql.seed import python_reference
from trustsql.warehouse import Warehouse


def main():
    settings = Settings()
    engine = make_engine(settings.warehouse_url)
    control_engine = make_engine(settings.control_database_url)
    if engine.dialect.name != "postgresql":
        raise SystemExit("This verification requires PostgreSQL.")
    checks = {}
    try:
        warehouse = Warehouse(engine, settings)
        checks["reader_ready"] = warehouse.ready()
        for name, query in [
            ("direct_write_rejected", "DELETE FROM analytics.orders WHERE false"),
            ("audit_access_rejected", "SELECT * FROM control.query_runs LIMIT 1"),
        ]:
            try:
                with engine.connect() as connection, connection.begin():
                    connection.execute(text(query))
                checks[name] = False
            except DBAPIError:
                checks[name] = True
        try:
            with engine.connect() as connection, connection.begin():
                connection.execute(text("SET LOCAL statement_timeout='50ms'"))
                connection.execute(text("SELECT pg_sleep(2)"))
            checks["statement_timeout"] = False
        except DBAPIError as exc:
            checks["statement_timeout"] = getattr(exc.orig, "sqlstate", "") == "57014"
        _, rows, _ = warehouse.execute(validate_sql(net_sql("2026-10-01", "2026-11-01")))
        checks["reference_metric"] = rows == [[python_reference()["net_revenue_cents"]]]
        checks["control_ready"] = ControlStore(control_engine).ready()
        catalog = Catalog(settings)
        try:
            checks["catalog_read"] = len(catalog.load()) == 6
        finally:
            catalog.close()
    finally:
        engine.dispose()
        control_engine.dispose()
    print(json.dumps(checks, indent=2))
    raise SystemExit(0 if all(checks.values()) else 1)


if __name__ == "__main__":
    main()
