import json
import logging
import secrets
import time
from contextlib import asynccontextmanager
from importlib.resources import files
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from trustsql import __version__
from trustsql.catalog import Catalog
from trustsql.config import Settings
from trustsql.control import ControlStore
from trustsql.db import make_engine
from trustsql.errors import TrustSQLError
from trustsql.inspection import change_impact, inspect_query
from trustsql.models import Answer, InspectRequest, Question
from trustsql.policy import validate_sql
from trustsql.service import QueryService
from trustsql.warehouse import Warehouse

logger = logging.getLogger("trustsql")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False
EXAMPLES = [
    "What was our net revenue last month?",
    "What was gross revenue last month?",
    "Top five products by gross revenue last month",
    "How many completed orders were there last month?",
    "Gross revenue by customer segment last month",
    "Show successful refunds for last month",
    "How many customers are in each region?",
    "What were captured payments last month?",
]


class BodyLimitMiddleware:
    def __init__(self, app, limit=8192):
        self.app, self.limit = app, limit

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in {"POST", "PUT", "PATCH"}:
            return await self.app(scope, receive, send)
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > self.limit:
                return await JSONResponse(
                    {"error": {"code": "body_too_large", "message": "The request exceeds the 8 KB limit."}},
                    status_code=413,
                )(scope, receive, send)
            if not message.get("more_body", False):
                break
        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, replay, send)


def create_app(settings: Settings | None = None, *, control_store=None):
    settings = settings or Settings()
    warehouse_engine = make_engine(settings.warehouse_url)
    control_engine = make_engine(settings.control_database_url)
    warehouse = Warehouse(warehouse_engine, settings)
    control = control_store if control_store is not None else ControlStore(control_engine)
    catalog = Catalog(settings)
    service = QueryService(settings, warehouse, control, catalog)

    @asynccontextmanager
    async def lifespan(_app):
        yield
        catalog.close()
        if hasattr(service.planner, "close"):
            service.planner.close()
        warehouse_engine.dispose()
        control_engine.dispose()

    app = FastAPI(
        title="TrustSQL",
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.environment != "production" else None,
    )
    app.state.service = service
    app.state.settings = settings
    app.add_middleware(BodyLimitMiddleware)
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=[h.strip() for h in settings.allowed_hosts.split(",")]
    )

    @app.middleware("http")
    async def observe(request: Request, call_next):
        request.state.request_id = str(uuid4())
        started = time.monotonic()
        try:
            response = await call_next(request)
        except Exception as exc:
            logger.error(
                json.dumps(
                    {
                        "event": "unhandled_error",
                        "request_id": request.state.request_id,
                        "type": type(exc).__name__,
                    }
                )
            )
            response = JSONResponse(
                {
                    "error": {
                        "code": "internal_error",
                        "message": "The request could not be completed. Use the request ID to investigate.",
                        "request_id": request.state.request_id,
                    }
                },
                status_code=500,
            )
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; font-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        )
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cache-Control"] = (
            "no-store" if request.url.path.startswith(("/api", "/health")) else "no-cache"
        )
        if response.status_code == 429:
            response.headers["Retry-After"] = "60"
        logger.info(
            json.dumps(
                {
                    "event": "http_request",
                    "request_id": request.state.request_id,
                    "method": request.method,
                    "status": response.status_code,
                    "duration_ms": int((time.monotonic() - started) * 1000),
                }
            )
        )
        return response

    @app.exception_handler(TrustSQLError)
    async def expected_error(request: Request, exc: TrustSQLError):
        return JSONResponse(
            {"error": {"code": exc.code, "message": exc.message, "request_id": request.state.request_id}},
            status_code=exc.status,
        )

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, _exc):
        return JSONResponse(
            {
                "error": {
                    "code": "invalid_request",
                    "message": "Provide a question of 4–2000 characters, with no extra fields.",
                    "request_id": request.state.request_id,
                }
            },
            status_code=422,
        )

    def authorize(request: Request):
        expected = settings.api_token.get_secret_value()
        if expected:
            supplied = request.headers.get("authorization", "")
            if not secrets.compare_digest(supplied.encode(), f"Bearer {expected}".encode()):
                raise TrustSQLError(
                    "unauthorized", "Enter a valid API token in Connection to access this workspace.", 401
                )

    protected = [Depends(authorize)]

    @app.get("/health/live")
    def live():
        return {"status": "alive", "version": __version__}

    @app.get("/health/ready", dependencies=protected)
    def ready():
        checks = {"control": control.ready(), "warehouse": warehouse.ready(), "metadata": False}
        try:
            checks["metadata"] = bool(catalog.load())
        except TrustSQLError:
            pass
        return JSONResponse(
            {"status": "ready" if all(checks.values()) else "not_ready", "checks": checks},
            status_code=200 if all(checks.values()) else 503,
        )

    @app.get("/api/status", dependencies=protected)
    def status():
        return {
            "version": __version__,
            "mode": settings.mode,
            "database": warehouse.dialect,
            "metadata_source": "datahub" if settings.mode == "live" else "snapshot",
            "as_of_date": settings.as_of_date.isoformat(),
            "max_rows": settings.max_rows,
            "examples": EXAMPLES,
            "storage_ready": control.ready() and warehouse.ready(),
        }

    @app.post("/api/query", response_model=Answer, dependencies=protected)
    def query(question: Question, request: Request):
        # Client-provided forwarding headers are intentionally ignored.
        rate_key = settings.api_token.get_secret_value() or (
            request.client.host if request.client else "local"
        )
        return service.answer(question.question, request.state.request_id, rate_key)

    @app.get("/api/catalog", dependencies=protected)
    def get_catalog():
        return {
            "datasets": [d.model_dump() for d in catalog.load()],
            "source": "datahub" if settings.mode == "live" else "snapshot",
        }

    @app.post("/api/inspect", dependencies=protected)
    def inspect_sql(body: InspectRequest, request: Request):
        key = settings.api_token.get_secret_value() or (request.client.host if request.client else "local")
        control.consume(key, settings.rate_limit_per_minute)
        if not service.slots.acquire(blocking=False):
            raise TrustSQLError("busy", "The analyst is at capacity. Retry shortly.", 503)
        try:
            datasets = catalog.load()
            if body.changed_table:
                target = next((d for d in datasets if d.table == body.changed_table), None)
                if target is None or (
                    body.changed_column and body.changed_column not in {c.name for c in target.columns}
                ):
                    raise TrustSQLError(
                        "invalid_change_target", "Choose a table and column from the approved catalog.", 422
                    )
            report = inspect_query(validate_sql(body.sql, warehouse.dialect), datasets, warehouse.dialect)
            report["executed"] = False
            if body.changed_table:
                report["impact"] = change_impact(report, body.changed_table, body.changed_column)
            return report
        finally:
            service.slots.release()

    @app.get("/api/runs", dependencies=protected)
    def runs():
        return {"runs": control.recent()}

    @app.get("/api/evaluations", dependencies=protected)
    def evaluations():
        path = Path("var/benchmark-summary.json")
        if not path.is_file():
            return {"state": "not_run", "message": "Run the offline evaluation CLI to create a report."}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise TrustSQLError(
                "report_unavailable",
                "The evaluation report could not be read. Re-run the offline evaluation.",
                503,
            ) from None

    assets = str(files("trustsql").joinpath("assets"))
    app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(Path(assets) / "index.html")

    return app


app = create_app()
