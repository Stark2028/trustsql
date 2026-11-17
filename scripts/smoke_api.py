"""Verify the packaged local app without printing credentials, SQL, or result rows."""

import hashlib
import json
import os
from pathlib import Path

import httpx
from dotenv import dotenv_values

from trustsql.seed import python_reference


def main():
    token = dotenv_values(".env.docker").get("TRUSTSQL_API_TOKEN", "")
    base = os.environ.get("TRUSTSQL_SMOKE_BASE_URL", "http://127.0.0.1:8088")
    checks = {}
    with httpx.Client(base_url=base, timeout=15, trust_env=False) as client:
        checks["public_liveness"] = client.get("/health/live").status_code == 200
        checks["authentication"] = client.get("/api/status").status_code == 401
        client.headers["Authorization"] = f"Bearer {token}"
        ready = client.get("/health/ready")
        checks["readiness"] = ready.status_code == 200 and ready.json().get("status") == "ready"
        status = client.get("/api/status").json()
        checks["postgresql_demo"] = status.get("mode") == "demo" and status.get("database") == "postgres"
        result = client.post("/api/query", json={"question": "What was our net revenue last month?"})
        if result.status_code == 200:
            answer = result.json()
            checks["reference_metric"] = answer["rows"] == [[python_reference()["net_revenue_cents"]]]
            checks["audit_trace"] = answer["stages"][-1]["name"] == "Audit"
        else:
            checks["reference_metric"] = checks["audit_trace"] = False
        clarified = client.post("/api/query", json={"question": "What was revenue last month?"})
        checks["clarification"] = (
            clarified.status_code == 200 and clarified.json()["status"] == "clarification"
        )
        checks["catalog"] = len(client.get("/api/catalog").json().get("datasets", [])) == 6
        checks["audit_history"] = bool(client.get("/api/runs").json().get("runs"))
        root = Path(__file__).resolve().parents[1] / "src" / "trustsql" / "assets"
        for name in ["app.js", "style.css", "mark.svg"]:
            response = client.get(f"/assets/{name}")
            checks[f"packaged_asset_{name}"] = (
                response.status_code == 200
                and hashlib.sha256(response.content).digest()
                == hashlib.sha256((root / name).read_bytes()).digest()
            )
        report = client.get("/api/evaluations").json()
        checks["evaluation_report"] = report.get("passed") == report.get("cases") == 18
    print(json.dumps(checks, indent=2))
    raise SystemExit(0 if all(checks.values()) else 1)


if __name__ == "__main__":
    main()
