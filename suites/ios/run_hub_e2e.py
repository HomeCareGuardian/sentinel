#!/usr/bin/env python3
"""J1/iOS — validate P0 hub HTTP endpoints against HUB_BASE_URL (live, no mocks)."""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass

import httpx

# P0 subset aligned with journeys/catalog.yaml and iOS HCGAPIEndpoint
P0_ENDPOINTS: list[tuple[str, str, tuple[int, ...]]] = [
    ("GET", "/health", (200,)),
    ("GET", "/api/health", (200,)),
    ("GET", "/api/status", (200,)),
    ("GET", "/api/devices", (200,)),
    ("GET", "/api/states", (200,)),
    ("GET", "/api/anomalies", (200,)),
    ("GET", "/api/users/me", (200, 404)),
    ("GET", "/api/dashboard", (200, 503)),
]


@dataclass
class Row:
    method: str
    path: str
    status: int | None
    ok: bool
    error: str | None = None


def main() -> int:
    hub = os.environ.get("HUB_BASE_URL", "").strip()
    if not hub:
        print("FAIL: HUB_BASE_URL is required for iOS hub E2E", file=sys.stderr)
        return 1
    hub = hub.rstrip("/")

    rows: list[Row] = []
    with httpx.Client(base_url=hub, timeout=20.0) as client:
        for method, path, expected in P0_ENDPOINTS:
            start = time.time()
            try:
                r = client.request(method, path)
                ok = r.status_code in expected
                rows.append(Row(method, path, r.status_code, ok))
                ms = (time.time() - start) * 1000
                mark = "OK" if ok else "FAIL"
                print(f"{mark} {method} {path} -> {r.status_code} ({ms:.0f}ms)")
            except Exception as exc:
                rows.append(Row(method, path, None, False, str(exc)))
                print(f"FAIL {method} {path} -> {exc}")

    failed = [x for x in rows if not x.ok]
    if failed:
        print(f"\n{len(failed)} hub endpoint(s) failed", file=sys.stderr)
        return 1
    print(f"\nAll {len(rows)} P0 hub endpoints passed against {hub}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
