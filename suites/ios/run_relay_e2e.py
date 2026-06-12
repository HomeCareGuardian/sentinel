#!/usr/bin/env python3
"""iOS Relay endpoints E2E regression tests."""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass

import httpx

@dataclass
class Row:
    method: str
    path: str
    status: int | None
    ok: bool
    error: str | None = None

def main() -> int:
    relay_url = os.environ.get("RELAY_BASE_URL", "").strip().rstrip("/")
    if not relay_url:
        print("SKIP: RELAY_BASE_URL not set", file=sys.stderr)
        return 0
    
    email = os.environ.get("E2E_USER_EMAIL", "").strip()
    password = os.environ.get("E2E_USER_PASSWORD", "").strip()
    if not email or not password:
        print("SKIP: E2E_USER_EMAIL or E2E_USER_PASSWORD not set", file=sys.stderr)
        return 0

    rows: list[Row] = []

    with httpx.Client(base_url=relay_url, timeout=20.0) as client:
        # 1. Login
        start = time.perf_counter()
        try:
            r = client.post("/api/app/login", json={"email": email, "password": password})
            ok = r.status_code == 200
            rows.append(Row("POST", "/api/app/login", r.status_code, ok))
            ms = (time.perf_counter() - start) * 1000
            mark = "OK" if ok else "FAIL"
            print(f"{mark} POST /api/app/login -> {r.status_code} ({ms:.0f}ms)")
            
            if not ok:
                print(f"FAIL: Login returned {r.status_code}: {r.text}", file=sys.stderr)
                # Appended to rows above, we skip the rest if login fails
                login_data = {}
            else:
                try:
                    login_data = r.json()
                except Exception as exc:
                    print(f"FAIL: Login response is not valid JSON: {exc}", file=sys.stderr)
                    login_data = {}
                    rows[-1].ok = False
                    rows[-1].error = "Invalid JSON"

            if not isinstance(login_data, dict):
                print(f"FAIL: Login response is not a JSON object: {login_data}", file=sys.stderr)
                login_data = {}
                rows[-1].ok = False

            token = login_data.get("token")
            if not token:
                print("FAIL: No token in login response", file=sys.stderr)
                rows[-1].ok = False
                
            # 2. Get /api/app/hubs
            if token:
                start = time.perf_counter()
                r = client.get("/api/app/hubs", headers={"Authorization": f"Bearer {token}"})
                ok = r.status_code == 200
                ms = (time.perf_counter() - start) * 1000
                
                if not ok:
                    rows.append(Row("GET", "/api/app/hubs", r.status_code, False, r.text))
                    print(f"FAIL GET /api/app/hubs -> {r.status_code} ({ms:.0f}ms)")
                else:
                    try:
                        data = r.json()
                        if not isinstance(data, dict):
                            raise ValueError("Response is not a JSON object")
                    except Exception as exc:
                        print(f"FAIL: Hubs response is not valid JSON: {exc}", file=sys.stderr)
                        rows.append(Row("GET", "/api/app/hubs", r.status_code, False, "Invalid JSON response"))
                        data = {}

                    if data:
                        hubs = data.get("hubs", [])
                        
                        if not hubs:
                            print(f"WARN GET /api/app/hubs -> {r.status_code} ({ms:.0f}ms) (0 hubs returned, cannot assert shape)")
                            rows.append(Row("GET", "/api/app/hubs", r.status_code, True))
                        else:
                            hub = hubs[0]
                            if "role" not in hub or "permissions" not in hub:
                                print(f"FAIL GET /api/app/hubs -> {r.status_code} ({ms:.0f}ms) (Missing role or permissions in hub payload)")
                                print(f"Payload: {hub}", file=sys.stderr)
                                rows.append(Row("GET", "/api/app/hubs", r.status_code, False, "Missing role or permissions"))
                            else:
                                print(f"OK GET /api/app/hubs -> {r.status_code} ({ms:.0f}ms) (Shape validated)")
                                rows.append(Row("GET", "/api/app/hubs", r.status_code, True))
                    
        except Exception as exc:
            print(f"FAIL Relay request -> {exc}", file=sys.stderr)
            rows.append(Row("Unknown", "Relay", None, False, str(exc)))

    failed = [x for x in rows if not x.ok]
    if failed:
        print(f"\n{len(failed)} relay endpoint(s) failed", file=sys.stderr)
        return 1
    print(f"\nAll {len(rows)} relay E2E checks passed against {relay_url}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
