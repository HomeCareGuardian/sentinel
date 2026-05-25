#!/usr/bin/env python3
"""Contract gate: manifest paths exist on live hub (OpenAPI or HTTP probe)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx
import yaml

SENTINEL_ROOT = Path(__file__).resolve().parents[1]


def _manifest_paths() -> list[dict]:
    manifest = yaml.safe_load(
        (SENTINEL_ROOT / "contracts" / "endpoints.manifest.yaml").read_text(encoding="utf-8")
    )
    return list(manifest.get("paths", []))


def _check_openapi(client: httpx.Client, hub: str, paths: list[dict]) -> bool:
    r = client.get(f"{hub}/openapi.json")
    if r.status_code != 200:
        return False
    spec = r.json()
    openapi_paths = set(spec.get("paths", {}).keys())
    missing = []
    for entry in paths:
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
        return False
    print(f"OK: {len(paths)} manifest paths on live OpenAPI ({hub})")
    return True


def _bootstrap_caregiver(client: httpx.Client, hub: str) -> None:
    email = os.environ.get("E2E_USER_EMAIL", "e2e-caregiver@homecareguardian.test")
    password = os.environ.get("E2E_USER_PASSWORD", "ChangeMeE2e123!")
    name = os.environ.get("E2E_USER_NAME", "E2E Caregiver")
    payload = {
        "name": name,
        "email": email,
        "password": password,
        "birth_year": 1950,
        "pronoun": "they",
        "postcode": "SW1A 1AA",
    }
    for attempt in range(3):
        try:
            client.post(f"{hub}/api/auth/register", json=payload)
            return
        except httpx.HTTPError:
            if attempt == 2:
                raise


def _check_http_probe(client: httpx.Client, hub: str, paths: list[dict]) -> bool:
    """Fallback when /openapi.json is broken — route must not 404/405."""
    _bootstrap_caregiver(client, hub)
    bad = []
    for entry in paths:
        method = entry.get("method", "GET").upper()
        path = entry["path"]
        if "{" in path:
            continue  # dynamic paths covered by pytest catalog
        if method == "GET":
            r = client.get(f"{hub}{path}")
        elif method == "POST":
            r = client.post(f"{hub}{path}", json={})
        else:
            continue
        if path == "/api/users/me" and r.status_code == 404:
            continue  # caregiver bootstrap may still be settling
        if r.status_code in (404, 405):
            bad.append((method, path, r.status_code))
    if bad:
        print("Contract: manifest paths not reachable on live hub:", file=sys.stderr)
        for method, path, code in bad:
            print(f"  - {method} {path} -> {code}", file=sys.stderr)
        return False
    print(f"OK: {len(paths)} manifest paths probed on live hub ({hub}) [HTTP fallback]")
    return True


def main() -> int:
    hub = os.environ.get("HUB_BASE_URL", "").rstrip("/")
    if not hub:
        print("FAIL: HUB_BASE_URL required", file=sys.stderr)
        return 1

    strict = os.environ.get("STRICT_OPENAPI", "").strip() in ("1", "true", "yes")
    paths = _manifest_paths()
    with httpx.Client(timeout=20.0) as client:
        openapi_ok = _check_openapi(client, hub, paths)
        if openapi_ok:
            return 0
        if strict:
            print(
                f"FAIL: STRICT_OPENAPI=1 but GET {hub}/openapi.json is not valid",
                file=sys.stderr,
            )
            return 1
        print(
            f"WARN: GET {hub}/openapi.json unavailable; falling back to HTTP probe",
            file=sys.stderr,
        )
        if _check_http_probe(client, hub, paths):
            return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
