"""Set the exact HTTPS host and verify the deployed app; never prints tokens or rows."""

import json
import subprocess
from urllib.parse import urlparse

import httpx
from deploy import ROOT, STACK, aws

stacks = aws("cloudformation", "describe-stacks", "--stack-name", STACK)
outputs = {o["OutputKey"]: o["OutputValue"] for o in stacks["Stacks"][0]["Outputs"]}
config = aws("lambda", "get-function-configuration", "--function-name", outputs["FunctionName"])
variables = config["Environment"]["Variables"]
variables["TRUSTSQL_ALLOWED_HOSTS"] = urlparse(outputs["Url"]).hostname
aws(
    "lambda",
    "update-function-configuration",
    payload={"FunctionName": outputs["FunctionName"], "Environment": {"Variables": variables}},
)
subprocess.run(
    [
        "aws",
        "lambda",
        "wait",
        "function-updated-v2",
        "--function-name",
        outputs["FunctionName"],
        "--region",
        "ap-south-1",
    ],
    check=True,
)
token = (ROOT / "api.env").read_text().strip().split("=", 1)[1]
checks = {}
with httpx.Client(base_url=outputs["Url"], timeout=60, follow_redirects=False) as client:
    checks["frontend"] = client.get("/").status_code == 200
    checks["authentication"] = client.get("/api/status").status_code == 401
    client.headers["Authorization"] = f"Bearer {token}"
    checks["ready"] = client.get("/health/ready").status_code == 200
    answer = client.post("/api/query", json={"question": "What was our net revenue last month?"})
    checks["query"] = answer.status_code == 200 and answer.json().get("rows") == [[49682520]]
    checks["durable_audit"] = bool(client.get("/api/runs").json().get("runs"))
    checks["no_paid_model"] = client.get("/api/status").json().get("mode") == "demo"
report = {"url": outputs["Url"], "checks": checks}
(ROOT / "verification.json").write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
raise SystemExit(0 if all(checks.values()) else 1)
