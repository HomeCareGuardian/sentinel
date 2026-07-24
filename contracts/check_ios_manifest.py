#!/usr/bin/env python3
"""Drift gate: every hub endpoint the iOS app calls must exist on the live hub.

Catches the failure class where the app ships calls to a route the hub
renamed or retired (e.g. the `/api/v1/*` prefix), which "sometimes works,
sometimes doesn't" depending on which surface a screen goes through.

Strategy:

* Preferred: live ``/openapi.json`` — exact path-set comparison
  (parametrised segments match positionally).
* Fallback while ``/openapi.json`` is broken (hcg#2505): HTTP probe.
  A route that is truly absent answers FastAPI's router 404
  (``{"detail": "Not Found"}``) or 405; handler-level 404s have
  endpoint-specific detail strings and count as present.

  Probe safety on a LIVE hub: GETs are always probed. POSTs are probed
  ONLY when the path is resource-scoped (contains an ``{id}`` segment) —
  a random probe id makes the handler 404 before any side effect. Bare
  action POSTs (``/api/ml/reset``, ``/api/devices/discover-network``, …)
  must never be fired at a live hub, so they are skipped and counted;
  they get full coverage in openapi mode.
"""

from __future__ import annotations

import os
import re
import sys
import uuid
from pathlib import Path

import yaml

SENTINEL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SENTINEL_ROOT))

from lib.hub_transport import make_hub_client  # noqa: E402

MANIFEST = SENTINEL_ROOT / "contracts" / "ios_hub_endpoints.manifest.yaml"


def _endpoints() -> list[dict]:
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    return list(data.get("endpoints", []))


def _norm(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "{}", path.rstrip("/"))


def _check_openapi(spec: dict, endpoints: list[dict]) -> list[str]:
    live: set[tuple[str, str]] = set()
    for path, methods in spec.get("paths", {}).items():
        for method in methods:
            live.add((method.lower(), _norm(path)))
    missing = []
    for entry in endpoints:
        method = entry["method"].lower()
        if (method, _norm(entry["path"])) not in live:
            missing.append(f"{entry['method']} {entry['path']}")
    return missing


ROUTER_404 = re.compile(r'^\{"detail"\s*:\s*"Not Found"\}$')


def _check_probe(client, endpoints: list[dict]) -> list[str]:
    probe_id = f"sentinel-drift-{uuid.uuid4()}"
    missing = []
    skipped = 0
    for entry in endpoints:
        method = entry["method"].upper()
        path_template = entry["path"]
        if method == "GET":
            r = client.get(path_template.replace("{id}", probe_id))
        elif method == "POST" and "{id}" in path_template:
            # Random id -> handler 404s before any side effect.
            r = client.post(path_template.replace("{id}", probe_id), json={})
        else:
            skipped += 1  # bare action POST / PUT / DELETE: not probe-safe live
            continue
        if r.status_code == 405 or (
            r.status_code == 404 and ROUTER_404.match(r.text.strip())
        ):
            missing.append(f"{method} {path_template} -> {r.status_code} (route absent)")
    if skipped:
        print(
            f"WARN: {skipped} non-probe-safe endpoints not checked in probe mode "
            "(covered once /openapi.json serves again — hcg#2505)",
            file=sys.stderr,
        )
    return missing


def main() -> int:
    hub = os.environ.get("HUB_BASE_URL", "").rstrip("/")
    if not hub:
        print("FAIL: HUB_BASE_URL required", file=sys.stderr)
        return 1
    endpoints = _endpoints()
    with make_hub_client(timeout=20.0) as client:
        r = client.get("/openapi.json")
        if r.status_code == 200:
            missing = _check_openapi(r.json(), endpoints)
            mode = "openapi"
        else:
            print(
                f"WARN: /openapi.json -> {r.status_code} (hcg#2505); "
                "falling back to HTTP probe",
                file=sys.stderr,
            )
            missing = _check_probe(client, endpoints)
            mode = "probe"
    if missing:
        print(
            f"Drift: iOS app calls endpoints absent from the live hub ({mode}):",
            file=sys.stderr,
        )
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        return 1
    print(f"OK: {len(endpoints)} iOS-called endpoints present on live hub [{mode}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
