"""Publish the exact committed tree via GitHub API when Git HTTPS is unavailable.

Only UTF-8 source trees are accepted. Tokens stay in process memory. Remote
updates are fast-forward only; locally reconstructed commits must match SHA-1.
"""

import base64
import hashlib
import itertools
import json
import subprocess
from datetime import datetime

import httpx


def git(*args, data=None):
    return subprocess.check_output(["git", *args], input=data)


def main():
    token = subprocess.check_output(["gh", "auth", "token"], text=True).strip()
    local = git("rev-parse", "HEAD").decode().strip()
    tree = git("rev-parse", "HEAD^{tree}").decode().strip()
    parents = git("show", "-s", "--format=%P", "HEAD").decode().split()
    metadata = (
        git("show", "-s", "--format=%an%x00%ae%x00%aI%x00%cn%x00%ce%x00%cI%x00%B", "HEAD")
        .decode()
        .split("\0", 6)
    )
    with httpx.Client(
        base_url="https://api.github.com/repos/Stark2028/trustsql",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
        timeout=60,
    ) as client:

        def api(method, path, body=None):
            response = client.request(method, path, json=body)
            if not response.is_success:
                raise RuntimeError(f"GitHub {method} {path}: HTTP {response.status_code}")
            return response.json()

        entries = []
        for record in git("ls-tree", "-rz", "HEAD").split(b"\0"):
            if not record:
                continue
            info, path = record.split(b"\t", 1)
            mode, kind, sha = info.decode().split()
            if kind != "blob":
                raise RuntimeError("Unsupported Git tree entry")
            entries.append(
                {
                    "path": path.decode(),
                    "mode": mode,
                    "type": "blob",
                    "content": git("cat-file", "blob", sha).decode("utf-8"),
                }
            )
        tree_response = client.post("/git/trees", json={"tree": entries})
        initialization_sha = None
        if tree_response.status_code == 409:
            # GitHub's Git API needs an initialized object database. Create a
            # helper commit only in a repository with no branches, then replace
            # exactly that helper reference with the scanned publication root.
            if api("GET", "/branches"):
                raise RuntimeError("Refusing initialization of a non-empty repository")
            readme = git("show", "HEAD:README.md")
            initialized = api(
                "PUT",
                "/contents/README.md",
                {
                    "message": "Initialize repository for verified source import",
                    "content": base64.b64encode(readme).decode(),
                },
            )
            initialization_sha = initialized["commit"]["sha"]
            remote_tree = api("POST", "/git/trees", {"tree": entries})["sha"]
        else:
            tree_response.raise_for_status()
            remote_tree = tree_response.json()["sha"]
        if remote_tree != tree:
            raise RuntimeError("Remote source tree does not match the scanned commit")
        commit = api(
            "POST",
            "/git/commits",
            {
                "message": metadata[6].rstrip("\n"),
                "tree": tree,
                "parents": parents,
                "author": {"name": metadata[0], "email": metadata[1], "date": metadata[2]},
                "committer": {"name": metadata[3], "email": metadata[4], "date": metadata[5]},
            },
        )
        sha = commit["sha"]
        existing = client.get("/git/ref/heads/main")
        if existing.status_code == 404:
            api("POST", "/git/refs", {"ref": "refs/heads/main", "sha": sha})
        else:
            existing.raise_for_status()
            helper_only = (
                initialization_sha is not None and existing.json()["object"]["sha"] == initialization_sha
            )
            api("PATCH", "/git/refs/heads/main", {"sha": sha, "force": helper_only})
        if sha != local:
            prefix = f"tree {tree}\n" + "".join(f"parent {p}\n" for p in parents)
            zones = [
                "+0000",
                datetime.fromisoformat(metadata[2]).strftime("%z"),
                datetime.fromisoformat(metadata[5]).strftime("%z"),
            ]
            found = None
            for az, cz, suffix in itertools.product(zones, zones, ["", "\n", "\n\n"]):
                author = commit["author"]
                committer = commit["committer"]
                a_time = int(datetime.fromisoformat(author["date"].replace("Z", "+00:00")).timestamp())
                c_time = int(datetime.fromisoformat(committer["date"].replace("Z", "+00:00")).timestamp())
                raw = (
                    prefix
                    + f"author {author['name']} <{author['email']}> {a_time} {az}\ncommitter {committer['name']} <{committer['email']}> {c_time} {cz}\n\n"
                    + commit["message"].rstrip("\n")
                    + suffix
                ).encode()
                if hashlib.sha1(b"commit " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == sha:
                    found = raw
                    break
            if found is None:
                raise RuntimeError("Published, but local commit reconstruction needs review")
            assert git("hash-object", "-t", "commit", "-w", "--stdin", data=found).decode().strip() == sha
            git("update-ref", "refs/heads/main", sha, local)
        git("update-ref", "refs/remotes/origin/main", sha)
        git("config", "branch.main.remote", "origin")
        git("config", "branch.main.merge", "refs/heads/main")
        print(
            json.dumps(
                {
                    "repository": "https://github.com/Stark2028/trustsql",
                    "commit": sha,
                    "tree_verified": True,
                    "local_branch_aligned": True,
                }
            )
        )


if __name__ == "__main__":
    main()
