"""Bound upstream reads before parsing untrusted JSON."""

import json

import httpx


def post_json(client: httpx.Client, url: str, *, headers: dict, payload: dict, max_bytes: int):
    with client.stream("POST", url, headers=headers, json=payload) as response:
        response.raise_for_status()
        size = 0
        chunks = []
        for chunk in response.iter_bytes(chunk_size=16384):
            size += len(chunk)
            if size > max_bytes:
                raise ValueError("Upstream response exceeds the configured limit")
            chunks.append(chunk)
        payload = json.loads(b"".join(chunks))
        if not isinstance(payload, dict):
            raise ValueError("Upstream JSON must be an object")
        return payload
