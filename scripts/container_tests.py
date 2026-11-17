"""Run tests with offline bootstrap credentials in a disposable test container.

Never prints connection strings. The serving app never receives owner credentials.
"""

import os

import pytest

os.environ["TRUSTSQL_TEST_POSTGRES_URL"] = os.environ["TRUSTSQL_BOOTSTRAP_URL"]
os.environ["TRUSTSQL_TEST_READER_URL"] = os.environ["TRUSTSQL_WAREHOUSE_URL"]
os.environ["TRUSTSQL_TEST_CONTROL_URL"] = os.environ["TRUSTSQL_CONTROL_DATABASE_URL"]
os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
raise SystemExit(
    pytest.main(
        [
            "/checks/tests",
            "-q",
            "-p",
            "no:cacheprovider",
            "-o",
            "markers=postgres: actual PostgreSQL integration check",
            "--basetemp",
            "/tmp/trustsql-tests",
        ]
    )
)
