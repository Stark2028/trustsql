import json
import os
import urllib.request

token = os.environ.get("TRUSTSQL_API_TOKEN", "")
request = urllib.request.Request(
    "http://127.0.0.1:8000/health/ready", headers={"Authorization": f"Bearer {token}"} if token else {}
)
try:
    with urllib.request.urlopen(request, timeout=4) as response:
        ready = json.load(response)["status"] == "ready"
except Exception:
    ready = False
raise SystemExit(0 if ready else 1)
