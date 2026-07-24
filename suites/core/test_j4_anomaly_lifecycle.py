"""J4 — Create, list, acknowledge anomaly on live hub."""

import pytest

pytestmark = [pytest.mark.sentinel_e2e, pytest.mark.j4]


def _cleanup_anomaly(hub_client, anomaly_id, admin_auth=None) -> None:
    """Best-effort teardown so J4 does not pollute /api/anomalies on the shared
    Pi. Never raises. On hub 0.1.10 the only working path is POST /resolve with
    admin auth and NO request body: DELETE is 405, and /resolve with any JSON
    body 500s on the hcg#2505 body-parse crash (a bodyless resolve dodges it)."""
    if not anomaly_id:
        return
    kwargs = {"auth": admin_auth} if admin_auth is not None else {}
    try:
        hub_client.post(f"/api/anomalies/{anomaly_id}/resolve", **kwargs)
    except Exception:
        pass


def _create_anomaly(hub_client, motion_entity_id: str) -> str:
    created = hub_client.post(
        "/api/anomalies",
        json={
            "entity_id": motion_entity_id,
            "anomaly_type": "e2e_j4",
            "severity": "warning",
            "message": "E2E J4 anomaly",
            "is_human_related": True,
        },
    )
    assert created.status_code in (200, 201), created.text
    body = created.json()
    anomaly_id = body.get("anomaly_id") or body.get("id")
    assert anomaly_id
    return anomaly_id


def test_anomaly_create_and_list(hub_client, motion_entity_id: str, admin_auth):
    anomaly_id = _create_anomaly(hub_client, motion_entity_id)
    try:
        listed = hub_client.get("/api/anomalies")
        assert listed.status_code == 200
        rows = listed.json()
        assert any(
            (row.get("anomaly_id") or row.get("id")) == anomaly_id
            for row in rows
            if isinstance(row, dict)
        )
    finally:
        _cleanup_anomaly(hub_client, anomaly_id, admin_auth)


@pytest.mark.xfail(strict=True, reason="hcg#2505 acknowledge body-parse crash")
def test_anomaly_acknowledge(hub_client, motion_entity_id: str, admin_auth):
    """Acknowledge 500s on hcg#2505 (JSON body-parse crash on the py3.14 image)
    before the handler even looks the anomaly up. Kept known-red via
    xfail(strict) so the P0 gate stays green while the bug is open; a clean 2xx
    (hub fixed) reports XPASS and fails loudly, prompting removal. Same failure
    class as the J7 body-parse probes."""
    anomaly_id = _create_anomaly(hub_client, motion_entity_id)
    try:
        ack_kwargs = {}
        if admin_auth is not None:
            ack_kwargs["auth"] = admin_auth
        else:
            ack_kwargs["headers"] = {"Authorization": "Bearer admin"}

        ack = hub_client.post(
            f"/api/anomalies/{anomaly_id}/acknowledge",
            json={"acknowledged_by": "e2e-j4"},
            **ack_kwargs,
        )
        if ack.status_code == 500 and "Admin authentication not configured" in ack.text:
            pytest.skip("hub ADMIN_USERNAME/ADMIN_PASSWORD not set on Pi")
        assert ack.status_code in (200, 201), ack.text
        ack_body = ack.json()
        assert ack_body.get("acknowledged_at") or ack_body.get("anomaly_id") == anomaly_id
    finally:
        _cleanup_anomaly(hub_client, anomaly_id, admin_auth)
