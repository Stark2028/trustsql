"""Scan staged contents without ever printing matching secret values."""

import re
import subprocess
from pathlib import Path

from dotenv import dotenv_values


def main():
    paths = (
        subprocess.check_output(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"])
        .decode()
        .split("\0")
    )
    secret_values = [
        str(v).encode()
        for p in [".env", ".env.docker", "var/aws/api.env"]
        if Path(p).exists()
        for k, v in dotenv_values(p).items()
        if v and any(t in k for t in ["KEY", "TOKEN", "PASSWORD"]) and len(str(v)) >= 12
    ]
    patterns = [
        re.compile(b"AK" + b"IA[A-Z0-9]{16}"),
        re.compile(b"gh" + b"p_[A-Za-z0-9]{30,}"),
        re.compile(b"sk-ant-" + b"fai-[A-Za-z0-9_-]{20,}"),
    ]
    failures = []
    for path in filter(None, paths):
        if path.startswith(("var/", "scratch/", "artifacts/", ".aws/")) or (
            Path(path).name.startswith(".env") and path != ".env.example"
        ):
            failures.append(path)
            continue
        data = subprocess.check_output(["git", "show", f":{path}"])
        if any(value in data for value in secret_values) or any(p.search(data) for p in patterns):
            failures.append(path)
    if failures:
        print("Publication blocked; review these files: " + ", ".join(failures))
        raise SystemExit(1)
    print(f"Secret scan passed for {sum(bool(p) for p in paths)} staged files")


if __name__ == "__main__":
    main()
