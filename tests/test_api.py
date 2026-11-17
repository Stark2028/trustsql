import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError

from trustsql.app import create_app
from trustsql.config import Settings


def test_health_and_security_headers(client):
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").json()["status"] == "ready"
    response = client.get("/")
    assert response.status_code == 200
    assert "script-src 'self'" in response.headers["Content-Security-Policy"]
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert len(response.headers["X-Request-ID"]) == 36
    assert client.get("/assets/app.js").status_code == 200


def test_protected_routes_require_bearer_token(settings):
    app = create_app(settings.model_copy(update={"api_token": SecretStr("owner-secret")}))
    with TestClient(app) as client:
        for path in ["/api/status", "/api/catalog", "/api/runs", "/api/evaluations", "/health/ready"]:
            assert client.get(path).status_code == 401
        assert client.post("/api/query", json={"question": "net revenue last month"}).status_code == 401
        assert client.post("/api/inspect", json={"sql": "SELECT * FROM orders"}).status_code == 401
        assert client.get("/api/status", headers={"Authorization": "Bearer wrong"}).status_code == 401
        assert client.get("/api/status", headers={"Authorization": "Bearer owner-secret"}).status_code == 200
        assert client.get("/health/live").status_code == 200


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"question": "x"},
        {"question": " " * 8},
        {"question": "x" * 2001},
        {"question": "Valid question", "sql": "DELETE FROM orders"},
        {"question": "text\u0000null"},
    ],
)
def test_invalid_requests_are_redacted(client, payload):
    response = client.post("/api/query", json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
    assert "DELETE" not in response.text


def test_actual_body_size_limit(client):
    assert client.post("/api/query", content=b"x" * 9000).status_code == 413


def test_untrusted_host_rejected(client):
    assert client.get("/", headers={"Host": "attacker.example"}).status_code == 400


def test_rate_limited_requests_return_retry_after(app):
    app.state.service.settings.rate_limit_per_minute = 1
    with TestClient(app) as client:
        assert client.post("/api/query", json={"question": "net revenue last month"}).status_code == 200
        response = client.post("/api/query", json={"question": "net revenue last month"})
        assert response.status_code == 429
        assert response.headers["Retry-After"] == "60"


def test_not_initialized_is_not_ready(settings):
    with TestClient(create_app(settings)) as client:
        assert client.get("/health/ready").status_code == 503


@pytest.mark.parametrize(
    "overrides",
    [
        {"environment": "production"},
        {"mode": "live"},
        {"warehouse_url": "sqlite:///same.db", "control_database_url": "sqlite:///same.db"},
    ],
)
def test_bad_configuration_fails_at_startup(overrides):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **overrides)
