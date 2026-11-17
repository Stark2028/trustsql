import pytest
from fastapi.testclient import TestClient

from trustsql.app import create_app
from trustsql.config import Settings
from trustsql.control import ControlStore
from trustsql.db import make_engine
from trustsql.seed import seed_warehouse


@pytest.fixture
def settings(tmp_path):
    return Settings(
        _env_file=None,
        environment="test",
        warehouse_url=f"sqlite:///{tmp_path / 'warehouse.db'}",
        control_database_url=f"sqlite:///{tmp_path / 'control.db'}",
    )


@pytest.fixture
def app(settings):
    warehouse = make_engine(settings.warehouse_url)
    control = make_engine(settings.control_database_url)
    seed_warehouse(warehouse)
    ControlStore(control).initialize()
    warehouse.dispose()
    control.dispose()
    return create_app(settings)


@pytest.fixture
def client(app):
    with TestClient(app) as client:
        yield client
