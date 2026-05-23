"""J3 — Bootstrap HA entity visible via hub."""

import pytest

pytestmark = [pytest.mark.sentinel_e2e, pytest.mark.j3]


def _entity_ids(payload) -> set[str]:
    if isinstance(payload, list):
        return {x.get("entity_id") for x in payload if isinstance(x, dict) and x.get("entity_id")}
    if isinstance(payload, dict):
        if "states" in payload and isinstance(payload["states"], list):
            return _entity_ids(payload["states"])
        # map entity_id -> state
        return {k for k in payload.keys() if "." in k}
    return set()


def test_states_endpoint_returns_live_data(hub_client, motion_entity_id: str):
    r = hub_client.get("/api/states")
    assert r.status_code == 200
    ids = _entity_ids(r.json())
    if motion_entity_id:
        assert motion_entity_id in ids, f"{motion_entity_id} not in {sorted(ids)[:20]}..."
    else:
        assert len(ids) > 0, "expected at least one entity from live hub /api/states"
