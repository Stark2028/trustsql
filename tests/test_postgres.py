import os

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError

from trustsql.control import ControlStore
from trustsql.db import make_engine
from trustsql.planner import net_sql
from trustsql.policy import validate_sql
from trustsql.seed import python_reference, seed_warehouse
from trustsql.warehouse import Warehouse


@pytest.mark.postgres
def test_postgres_role_boundaries_and_metric(settings):
    url = os.environ.get("TRUSTSQL_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Set TRUSTSQL_TEST_POSTGRES_URL for disposable CI database")
    owner = make_engine(url)
    reader = make_engine(
        os.environ.get("TRUSTSQL_TEST_READER_URL")
        or make_url(url)
        .set(username="trustsql_reader", password="ci-reader-only")
        .render_as_string(hide_password=False)
    )
    control_engine = make_engine(
        os.environ.get("TRUSTSQL_TEST_CONTROL_URL")
        or make_url(url)
        .set(username="trustsql_control", password="ci-control-only")
        .render_as_string(hide_password=False)
    )
    try:
        seed_warehouse(owner)
        store = ControlStore(control_engine)
        store.initialize()
        warehouse = Warehouse(reader, settings)
        assert warehouse.ready()
        _, rows, _ = warehouse.execute(validate_sql(net_sql("2026-10-01", "2026-11-01")))
        assert rows == [[python_reference()["net_revenue_cents"]]]
        for query in ["DELETE FROM analytics.orders WHERE false", "SELECT * FROM control.query_runs"]:
            with pytest.raises(DBAPIError), reader.connect() as connection:
                connection.execute(text(query))
        with pytest.raises(DBAPIError) as raised, reader.connect() as connection:
            connection.execute(text("SET LOCAL statement_timeout='50ms'"))
            connection.execute(text("SELECT pg_sleep(2)"))
        assert raised.value.orig.sqlstate == "57014"
    finally:
        owner.dispose()
        reader.dispose()
        control_engine.dispose()
