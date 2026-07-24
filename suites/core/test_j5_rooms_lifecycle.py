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
    created_ok = False
    try:
        created = hub_client.post(
            "/api/rooms",
            json={"room_id": ROOM_ID, "name": ROOM_NAME},
            auth=admin_auth,
        )
        if created.status_code == 503:
            pytest.skip("rooms DB not configured on hub")
        assert created.status_code in (200, 201), created.text[:300]
        created_ok = True

        listed = hub_client.get("/api/rooms")
        assert listed.status_code == 200
        assert ROOM_ID in _room_ids(listed.json()), "created room missing from /api/rooms"

        # Happy-path delete: only here do we assert the delete succeeded.
        deleted = hub_client.delete(f"/api/rooms/{ROOM_ID}", auth=admin_auth)
        assert deleted.status_code == 200, deleted.text[:300]
        created_ok = False

        listed = hub_client.get("/api/rooms")
        assert listed.status_code == 200
        assert ROOM_ID not in _room_ids(listed.json()), "room still listed after delete"
    finally:
        # Best-effort cleanup only when a create actually landed and the
        # happy-path delete did not already run. Never hard-assert here: a
        # skip or an assertion failure before create must not be masked by a
        # 404 from deleting a room that was never made.
        if created_ok:
            try:
                hub_client.delete(f"/api/rooms/{ROOM_ID}", auth=admin_auth)
            except Exception:
                pass
