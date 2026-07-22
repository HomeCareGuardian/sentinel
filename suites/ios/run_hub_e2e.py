#!/usr/bin/env python3
"""J1/iOS — validate P0 hub HTTP endpoints against HUB_BASE_URL (live, no mocks)."""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from lib.hub_transport import make_hub_client  # noqa: E402

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
    hub = os.environ.get("HUB_BASE_URL", "").strip().rstrip("/")
    relay_url = os.environ.get("RELAY_BASE_URL", "").strip().rstrip("/")
    email = os.environ.get("E2E_USER_EMAIL", "").strip()
    password = os.environ.get("E2E_USER_PASSWORD", "").strip()

    if relay_url and email and password:
        # Use relay proxy approach
        print(
            f"INFO: RELAY_BASE_URL is set, routing hub E2E tests through relay proxy at {relay_url}"
        )
        try:
            with httpx.Client(base_url=relay_url, timeout=10.0) as auth_client:
                r_auth = auth_client.post(
                    "/api/app/login", json={"email": email, "password": password}
                )
                if r_auth.status_code != 200:
                    print(
                        f"FAIL: Relay login failed -> {r_auth.status_code}: {r_auth.text}",
                        file=sys.stderr,
                    )
                    return 1
                token = r_auth.json().get("token")

                r_hubs = auth_client.get(
                    "/api/app/hubs", headers={"Authorization": f"Bearer {token}"}
                )
                if r_hubs.status_code != 200:
                    print(
                        f"FAIL: Relay get hubs failed -> {r_hubs.status_code}: {r_hubs.text}",
                        file=sys.stderr,
                    )
                    return 1

                hubs = r_hubs.json().get("hubs", [])
                if not hubs:
                    print("FAIL: No hubs found for user in relay", file=sys.stderr)
                    return 1

                device_id = hubs[0].get("device_id")

            hub = f"{relay_url}/api/hubs/{device_id}/proxy"
            headers = {"Authorization": f"Bearer {token}"}
            print(f"INFO: Authenticated and resolved proxy path for hub {device_id}")
        except Exception as exc:
            print(f"FAIL: Relay auth setup failed -> {exc}", file=sys.stderr)
            return 1
    else:
        # Fallback to direct hub connection
        if not hub:
            print(
                "FAIL: HUB_BASE_URL or (RELAY_BASE_URL + E2E_USER credentials) is required for iOS hub E2E",
                file=sys.stderr,
            )
            return 1
        headers = {}
        print(f"INFO: No relay config found. Falling back to direct hub URL: {hub}")

    if headers:
        client_cm = httpx.Client(base_url=hub, headers=headers, timeout=20.0)
    else:
        client_cm = make_hub_client(timeout=20.0, base_url=hub)

    rows: list[Row] = []
    with client_cm as client:
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
