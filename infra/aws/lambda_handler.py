"""Synthetic, credential-free model demo; PostgreSQL stays in the full Docker edition."""
# ruff: noqa: E402 -- cold-start paths must be set before application imports

import os

# Configure writable scratch paths before importing the ASGI app module.
os.environ["TRUSTSQL_WAREHOUSE_URL"] = "sqlite:////tmp/trustsql-warehouse.db"
os.environ["TRUSTSQL_CONTROL_DATABASE_URL"] = "sqlite:////tmp/trustsql-unused-control.db"
os.environ["TRUSTSQL_ENVIRONMENT"] = "development"
os.environ["TRUSTSQL_MODE"] = "demo"
os.environ["TRUSTSQL_LLM_API_KEY"] = ""
os.environ["TRUSTSQL_DATAHUB_TOKEN"] = ""
os.chdir("/tmp")

import boto3
from mangum import Mangum

from trustsql.config import Settings
from trustsql.db import make_engine
from trustsql.dynamo_control import DynamoControlStore
from trustsql.seed import seed_warehouse

settings = Settings(_env_file=None)
if len(settings.api_token.get_secret_value()) < 32:
    raise RuntimeError("Hosted demo requires an owner token")
engine = make_engine(settings.warehouse_url)
seed_warehouse(engine)
engine.dispose()
from trustsql.app import create_app

control = DynamoControlStore(boto3.resource("dynamodb").Table(os.environ["TRUSTSQL_AUDIT_TABLE"]))
app = create_app(settings, control_store=control)
handler = Mangum(app, lifespan="off")
