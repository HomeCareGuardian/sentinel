"""J1 — Hub boots and reports healthy."""

import pytest

pytestmark = [pytest.mark.sentinel_e2e, pytest.mark.j1]


def test_health_endpoint(hub_client):
    r = hub_client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert "status" in data
    assert str(data["status"]).lower() in ("healthy", "ok", "running")


def test_api_health_alias(hub_client):
    r = hub_client.get("/api/health")
    assert r.status_code == 200


def test_api_status(hub_client):
    r = hub_client.get("/api/status")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, dict)
    assert (
        "running" in data
        or "status" in data
        or "components" in data
    )


def test_api_devices(hub_client):
    """Live Pi hub — e.g. http://hcg-hub-5fcf7e73cfe7a329.local:8080/api/devices"""
    r = hub_client.get("/api/devices")
    assert r.status_code == 200, r.text[:300]
    data = r.json()
    assert "devices" in data
    assert isinstance(data["devices"], list)
