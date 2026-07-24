"""J7 — JSON-body parse probes for write endpoints (regression hcg#2505).

Nested-scope pydantic models became unresolvable ForwardRefs on the
Python 3.14 runtime image: any request that actually carried a JSON body
crashed with 500 *before the handler ran*, while body-less requests (and
unit tests on an older CI Python) stayed green.

These probes send a well-formed body at a nonexistent resource, so the
correct answer is a 4xx from the handler. A 500 means request parsing
itself is broken — the hcg#2505 failure class — with zero risk of
mutating live data.
"""

from __future__ import annotations

import uuid

import pytest

pytestmark = [pytest.mark.sentinel_e2e, pytest.mark.j7]

MISSING = f"e2e-missing-{uuid.uuid4()}"

# Plausible non-500 answers for a well-formed body at a nonexistent resource.
# Auth ordering / validation can legitimately answer before the handler 404s,
# and none of those are the hcg#2505 crash class. Only a 500 is the failure.
OK_4XX = (400, 401, 403, 404, 422)

# These three probes stay red on a hub that still carries hcg#2505 (they get a
# 500, which trips the ``!= 500`` assert). xfail(strict=True) keeps the P0 gate
# green while the bug is open, yet an unexpected PASS (hub fixed -> a clean 4xx)
# reports XPASS and fails loudly, prompting removal of the marker.
KNOWN_RED_2505 = pytest.mark.xfail(strict=True, reason="hcg#2505 body-parse crash")


def _admin_kwargs(admin_auth) -> dict:
    if admin_auth is None:
        pytest.skip("ADMIN_USERNAME/ADMIN_PASSWORD not set")
    return {"auth": admin_auth}


@KNOWN_RED_2505
def test_acknowledge_parses_json_body(hub_client, admin_auth):
    r = hub_client.post(
        f"/api/anomalies/{MISSING}/acknowledge",
        json={"acknowledged_by": "sentinel-j7"},
        **_admin_kwargs(admin_auth),
    )
    assert r.status_code != 500, "500 here means body parsing crashed (hcg#2505)"
    assert r.status_code in OK_4XX, (
        f"expected a 4xx for unknown anomaly, got {r.status_code}"
    )


@KNOWN_RED_2505
def test_resolve_parses_json_body(hub_client, admin_auth):
    r = hub_client.post(
        f"/api/anomalies/{MISSING}/resolve",
        json={},
        **_admin_kwargs(admin_auth),
    )
    assert r.status_code != 500, "500 here means body parsing crashed (hcg#2505)"
    assert r.status_code in OK_4XX, (
        f"expected a 4xx for unknown anomaly, got {r.status_code}"
    )


@KNOWN_RED_2505
def test_place_name_parses_json_body(hub_client):
    r = hub_client.post(
        f"/api/places/{MISSING}/name",
        json={"name": "Sentinel Probe", "category": "other"},
    )
    assert r.status_code != 500, "500 here means body parsing crashed (hcg#2505)"
    assert r.status_code in OK_4XX + (503,), (
        f"expected a 4xx for unknown place, got {r.status_code}"
    )


def test_runtime_settings_patch_parses_json_body(hub_client, admin_auth):
    """Empty patch must be rejected by validation (400/422), not crash."""
    r = hub_client.patch(
        "/api/hub/runtime-settings",
        json={},
        **_admin_kwargs(admin_auth),
    )
    assert r.status_code in (400, 422, 503), r.text[:300]
