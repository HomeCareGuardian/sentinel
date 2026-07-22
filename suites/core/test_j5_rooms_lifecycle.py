"""J5 — Room create / list / delete round trip (admin write path)."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.sentinel_e2e, pytest.mark.j5]

ROOM_ID = "e2e-sentinel-room"
ROOM_NAME = "E2E Sentinel Room"


def _room_ids(payload) -> set[str]:
    rows = payload.get("rooms") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        return set()
    return {r.get("room_id") for r in rows if isinstance(r, dict)}


def test_room_create_list_delete(hub_client, admin_auth):
    if admin_auth is None:
        pytest.skip("ADMIN_USERNAME/ADMIN_PASSWORD not set")
    try:
        created = hub_client.post(
            "/api/rooms",
            json={"room_id": ROOM_ID, "name": ROOM_NAME},
            auth=admin_auth,
        )
        if created.status_code == 503:
            pytest.skip("rooms DB not configured on hub")
        assert created.status_code in (200, 201), created.text[:300]

        listed = hub_client.get("/api/rooms")
        assert listed.status_code == 200
        assert ROOM_ID in _room_ids(listed.json()), "created room missing from /api/rooms"
    finally:
        deleted = hub_client.delete(f"/api/rooms/{ROOM_ID}", auth=admin_auth)
        assert deleted.status_code == 200, deleted.text[:300]

    listed = hub_client.get("/api/rooms")
    assert listed.status_code == 200
    assert ROOM_ID not in _room_ids(listed.json()), "room still listed after delete"
