#!/usr/bin/env python3
"""Black-box contract: endpoints.manifest paths exist on live hub OpenAPI."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx
import yaml

SENTINEL_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    hub = os.environ.get("HUB_BASE_URL", "").rstrip("/")
    if not hub:
        print("FAIL: HUB_BASE_URL required", file=sys.stderr)
        return 1

    manifest = yaml.safe_load(
        (SENTINEL_ROOT / "contracts" / "endpoints.manifest.yaml").read_text(encoding="utf-8")
    )

    with httpx.Client(timeout=20.0) as client:
        r = client.get(f"{hub}/openapi.json")
        if r.status_code != 200:
            print(f"FAIL: GET {hub}/openapi.json -> {r.status_code}", file=sys.stderr)
            return 1
        spec = r.json()

    openapi_paths = set(spec.get("paths", {}).keys())
    missing = []
    for entry in manifest.get("paths", []):
        path = entry["path"]
        if path in openapi_paths:
            continue
        if "{" in path:
            prefix = path.split("{", 1)[0].rstrip("/") or path
            if any(p.startswith(prefix) for p in openapi_paths):
                continue
        missing.append(path)

    if missing:
        print("Contract: manifest paths missing from live OpenAPI:", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        return 1

    print(f"OK: {len(manifest.get('paths', []))} manifest paths on live OpenAPI ({hub})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
