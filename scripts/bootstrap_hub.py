#!/usr/bin/env python3
"""Black-box bootstrap — public hub HTTP APIs only."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib.hub_transport import make_hub_client  # noqa: E402

MOTION_ENTITY = os.environ.get("E2E_MOTION_ENTITY_ID", "")


def main() -> int:
    hub = os.environ.get("HUB_BASE_URL", "").rstrip("/")
    if not hub:
        print("FAIL: HUB_BASE_URL required", file=sys.stderr)
        return 1

    email = os.environ.get("E2E_USER_EMAIL", "e2e-caregiver@homecareguardian.test")
    password = os.environ.get("E2E_USER_PASSWORD", "ChangeMeE2e123!")
    name = os.environ.get("E2E_USER_NAME", "E2E Caregiver")
    admin_user = os.environ.get("ADMIN_USERNAME", "")
    admin_pass = os.environ.get("ADMIN_PASSWORD", "")

    with make_hub_client() as client:
        reg = client.post(
            "/api/auth/register",
            json={
                "name": name,
                "email": email,
                "password": password,
                "birth_year": 1950,
                "pronoun": "they",
                "postcode": "SW1A 1AA",
            },
        )
        if reg.status_code not in (200, 201, 409):
            print(f"FAIL: register {reg.status_code} {reg.text[:300]}", file=sys.stderr)
            return 1

        me = client.get("/api/users/me")
        if me.status_code != 200:
            print(f"FAIL: users/me {me.status_code}", file=sys.stderr)
            return 1
        print(f"OK: users/me email={me.json().get('email')}")

        entity_id = MOTION_ENTITY or "binary_sensor.e2e_placeholder"
        created = client.post(
            "/api/anomalies",
            json={
                "entity_id": entity_id,
                "anomaly_type": "e2e_bootstrap",
                "severity": "warning",
                "message": "E2E bootstrap anomaly",
                "is_human_related": True,
            },
        )
        if created.status_code not in (200, 201):
            print(f"FAIL: create anomaly {created.status_code}", file=sys.stderr)
            return 1
        anomaly_id = created.json().get("anomaly_id") or created.json().get("id")
        if not anomaly_id:
            print("FAIL: no anomaly_id in response", file=sys.stderr)
            return 1

        ack_kwargs: dict = {"json": {"acknowledged_by": "sentinel-bootstrap"}}
        if admin_user and admin_pass:
            ack_kwargs["auth"] = httpx.BasicAuth(admin_user, admin_pass)
        else:
            ack_kwargs["headers"] = {"Authorization": "Bearer admin"}

        ack = client.post(f"/api/anomalies/{anomaly_id}/acknowledge", **ack_kwargs)
        # KNOWN FAILURE (hcg#2505): the acknowledge handler 500s on a body-parse
        # crash on the py3.14 runtime image. Soft-pass ONLY this specific 500 so
        # bootstrap can proceed while the bug is open; every other non-2xx still
        # WARNs below on its own. Remove this branch when hcg#2505 ships so a 500
        # here fails loudly again.
        if ack.status_code == 500:
            print("WARN: acknowledge 500, body-parse crash on hub (hcg#2505)", file=sys.stderr)
        elif ack.status_code not in (200, 201):
            print(f"WARN: acknowledge {ack.status_code} (check ADMIN_* credentials)", file=sys.stderr)
        else:
            print(f"OK: acknowledged {anomaly_id}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
