"""J6 — Caregiver logbook note linked to an anomaly (write path)."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.sentinel_e2e, pytest.mark.j6]


def _cleanup_anomaly(hub_client, anomaly_id, admin_auth=None) -> None:
    """Best-effort teardown so J6 does not pollute /api/anomalies on the
    shared Pi. Never raises. On hub 0.1.10 the only working path is POST
    /resolve with admin auth and NO request body: DELETE is 405, and /resolve
    with any JSON body 500s on the hcg#2505 body-parse crash (a bodyless
    resolve dodges it)."""
    if not anomaly_id:
        return
    kwargs = {"auth": admin_auth} if admin_auth is not None else {}
    try:
        hub_client.post(f"/api/anomalies/{anomaly_id}/resolve", **kwargs)
    except Exception:
        pass


def test_logbook_note_create(hub_client, admin_auth):
    created = hub_client.post(
        "/api/anomalies",
        json={
            "entity_id": "binary_sensor.e2e_placeholder",
            "anomaly_type": "e2e_j6",
            "severity": "warning",
            "message": "E2E J6 anomaly for logbook note",
            "is_human_related": True,
        },
    )
    assert created.status_code in (200, 201), created.text[:300]
    anomaly_id = created.json().get("anomaly_id") or created.json().get("id")
    assert anomaly_id

    try:
        note = hub_client.post(
            "/api/logbook/notes",
            json={"alert_id": anomaly_id, "note": "Sentinel J6 note"},
        )
        if note.status_code == 503:
            pytest.skip("logbook notes DB not configured on hub")
        if note.status_code == 404:
            pytest.skip("no caregiver registered on hub (register bootstrap required)")
        assert note.status_code in (200, 201), note.text[:300]
        body = note.json()
        text = body.get("note") or (body.get("data") or {}).get("note")
        assert text == "Sentinel J6 note", body

        listed = hub_client.get("/api/logbook")
        assert listed.status_code == 200
    finally:
        _cleanup_anomaly(hub_client, anomaly_id, admin_auth)


def test_logbook_note_rejects_empty(hub_client):
    r = hub_client.post("/api/logbook/notes", json={"alert_id": "x", "note": "  "})
    assert r.status_code in (400, 404, 503), r.text[:300]
    assert r.status_code != 500
