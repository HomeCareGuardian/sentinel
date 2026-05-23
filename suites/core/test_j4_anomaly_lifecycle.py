"""J4 — Create, list, acknowledge anomaly on live hub."""

import pytest

pytestmark = [pytest.mark.sentinel_e2e, pytest.mark.j4]


def test_anomaly_create_list_acknowledge(hub_client, motion_entity_id: str, admin_auth):
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

    listed = hub_client.get("/api/anomalies")
    assert listed.status_code == 200
    rows = listed.json()
    assert any(
        (row.get("anomaly_id") or row.get("id")) == anomaly_id for row in rows if isinstance(row, dict)
    )

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
    assert ack.status_code in (200, 201), ack.text
    ack_body = ack.json()
    assert ack_body.get("acknowledged_at") or ack_body.get("anomaly_id") == anomaly_id
