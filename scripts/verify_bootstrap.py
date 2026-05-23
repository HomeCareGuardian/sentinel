#!/usr/bin/env python3
"""Verify live hub matches bootstrap manifest (black-box HTTP)."""

from __future__ import annotations

import argparse
import os
import sys

import httpx
import yaml


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hub-url", required=True)
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args()

    manifest = yaml.safe_load(open(args.manifest, encoding="utf-8"))
    hub = args.hub_url.rstrip("/")
    motion_id = manifest.get("homeassistant", {}).get("motion_entity_id") or os.environ.get(
        "E2E_MOTION_ENTITY_ID", ""
    )
    email = os.environ.get(manifest.get("users", {}).get("email_env", "E2E_USER_EMAIL"), "")

    with httpx.Client(base_url=hub, timeout=20.0) as client:
        health = client.get("/health")
        if health.status_code != 200:
            print(f"FAIL: /health {health.status_code}")
            return 1

        me = client.get("/api/users/me")
        if me.status_code != 200:
            print(f"FAIL: /api/users/me {me.status_code}")
            return 1
        if email and me.json().get("email") != email:
            print(f"FAIL: email mismatch")
            return 1

        states = client.get("/api/states")
        if states.status_code != 200:
            print(f"FAIL: /api/states {states.status_code}")
            return 1
        payload = states.json()
        if motion_id:
            ids = set()
            if isinstance(payload, list):
                ids = {x.get("entity_id") for x in payload if isinstance(x, dict)}
            elif isinstance(payload, dict):
                ids = {k for k in payload if "." in k}
            if motion_id not in ids:
                print(f"WARN: {motion_id} not in states (hub may not expose test entity)")
        else:
            if isinstance(payload, list) and len(payload) == 0:
                print("WARN: /api/states empty")

        anomalies = client.get("/api/anomalies")
        if anomalies.status_code != 200:
            print(f"FAIL: /api/anomalies {anomalies.status_code}")
            return 1
        min_a = manifest.get("hub", {}).get("min_anomalies_after_seed", 1)
        if len(anomalies.json()) < min_a:
            print(f"FAIL: anomalies count < {min_a}")
            return 1

    print("Bootstrap verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
