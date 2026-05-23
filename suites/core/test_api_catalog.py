"""Full hub GET catalog — live black-box smoke against HUB_BASE_URL."""

from __future__ import annotations

import os

import httpx
import pytest

from suites.core.hub_catalog import load_catalog_entries

pytestmark = [pytest.mark.sentinel_e2e, pytest.mark.api_catalog]

FAIL_STATUSES = frozenset({405, 502, 504})


def _catalog_params():
    rows = []
    for entry in load_catalog_entries():
        path = entry["path"]
        query = entry.get("query")
        if query:
            path = f"{path}?{query}"
        expect = tuple(entry.get("expect", [200]))
        auth = entry.get("auth", "none")
        rows.append(pytest.param(path, expect, auth, id=entry["path"]))
    return rows


@pytest.fixture(scope="session", autouse=True)
def ensure_caregiver_registered(hub_client: httpx.Client) -> None:
    """So /api/users/me can return 200 during catalog runs."""
    email = os.environ.get("E2E_USER_EMAIL", "e2e-caregiver@homecareguardian.test")
    password = os.environ.get("E2E_USER_PASSWORD", "ChangeMeE2e123!")
    name = os.environ.get("E2E_USER_NAME", "E2E Caregiver")
    hub_client.post(
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


@pytest.mark.parametrize("path,expect,auth", _catalog_params())
def test_catalog_get(hub_client: httpx.Client, admin_auth, path: str, expect: tuple, auth: str):
    kwargs: dict = {}
    if auth == "admin" and admin_auth is not None:
        kwargs["auth"] = admin_auth
    r = hub_client.get(path, **kwargs)
    assert r.status_code not in FAIL_STATUSES, f"{path} -> {r.status_code} {r.text[:200]}"
    assert r.status_code in expect, f"{path} -> {r.status_code}, expected one of {expect}"


def test_device_detail_endpoints(hub_client: httpx.Client):
    listed = hub_client.get("/api/devices")
    assert listed.status_code == 200
    devices = listed.json().get("devices") or []
    if not devices:
        pytest.skip("no devices on hub")
    device_id = devices[0]["device_id"]
    for suffix in ("", "/config", "/detail", "/rooms"):
        path = f"/api/devices/{device_id}{suffix}"
        r = hub_client.get(path)
        assert r.status_code not in FAIL_STATUSES
        assert r.status_code in (200, 401, 403, 404, 500, 503), f"{path} -> {r.status_code}"


def test_state_by_entity_id(hub_client: httpx.Client):
    listed = hub_client.get("/api/states")
    assert listed.status_code == 200
    payload = listed.json()
    entity_id = None
    if isinstance(payload, dict):
        for key in payload:
            if "." in key:
                entity_id = key
                break
        if not entity_id and "states" in payload and payload["states"]:
            first = payload["states"][0]
            if isinstance(first, dict):
                entity_id = first.get("entity_id")
    elif isinstance(payload, list) and payload:
        entity_id = payload[0].get("entity_id")
    if not entity_id:
        pytest.skip("no entities in /api/states")
    r = hub_client.get(f"/api/states/{entity_id}")
    assert r.status_code not in FAIL_STATUSES
    assert r.status_code in (200, 404, 500, 503)
