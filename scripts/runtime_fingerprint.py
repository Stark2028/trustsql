"""Print source fingerprints and hardening flags, never runtime secrets."""

import hashlib
import json
import os
from importlib.resources import files

root = files("trustsql")
names = [
    "app.py",
    "catalog.py",
    "config.py",
    "control.py",
    "http.py",
    "models.py",
    "planner.py",
    "policy.py",
    "service.py",
    "warehouse.py",
    "evaluation.py",
    "seed.py",
    "cli.py",
    "inspection.py",
]
print(
    json.dumps(
        {
            "source_sha256": {
                name: hashlib.sha256(root.joinpath(name).read_bytes()).hexdigest() for name in names
            },
            "non_root": os.getuid() == 10001,
            "bootstrap_credentials_absent": "TRUSTSQL_BOOTSTRAP_URL" not in os.environ,
            "readonly_root": not os.access("/app", os.W_OK),
        },
        indent=2,
    )
)
