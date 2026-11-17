"""Create the user-authorized public repository using the existing gh credential."""

import json
import subprocess

import httpx

token = subprocess.check_output(["gh", "auth", "token"], text=True).strip()
with httpx.Client(
    timeout=60, headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
) as client:
    user = client.get("https://api.github.com/user")
    user.raise_for_status()
    login = user.json()["login"]
    target = f"https://api.github.com/repos/{login}/trustsql"
    existing = client.get(target)
    if existing.status_code == 404:
        result = client.post(
            "https://api.github.com/user/repos",
            json={
                "name": "trustsql",
                "description": "Metadata-aware SQL analyst with column lineage, semantic join checks, schema impact, and reproducible evaluation",
                "private": False,
                "auto_init": False,
            },
        )
        if result.status_code != 201:
            raise SystemExit(
                f"Repository creation failed with HTTP {result.status_code}; no credentials printed."
            )
        repo = result.json()
    elif existing.status_code == 200:
        raise SystemExit("A repository named trustsql already exists; inspect before modifying it.")
    else:
        raise SystemExit(f"Repository check failed with HTTP {existing.status_code}.")
    subprocess.run(["git", "remote", "add", "origin", repo["clone_url"]], check=True)
    print(json.dumps({"repository": repo["html_url"], "visibility": "public"}))
