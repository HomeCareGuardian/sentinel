"""J0 — LAN-gate posture: hubs past setup refuse direct LAN production calls.

Verifies the hcg#640 / hcg#2333 source-aware gate from the outside:

* liveness + setup-allowlist paths always serve to a direct LAN caller;
* production routes answer 403 ``production_lan_refused`` to a direct LAN
  caller once the hub is past setup mode;
* the loopback path (how the relay reaches the hub) still serves them.

These tests use ``lan_client`` (always direct, never ssh-exec) because they
are about what a caller on the LAN wire sees. They skip when the hub is
not directly reachable over LAN (e.g. off-site run via ssh-exec only) or
when the gate is not enforced (setup mode / observe-only rollout).
"""

from __future__ import annotations

import httpx
import pytest

pytestmark = [pytest.mark.sentinel_e2e, pytest.mark.j0]

PRODUCTION_ROUTES = ["/api/status", "/api/states", "/api/anomalies", "/api/dashboard"]
ALLOWLIST_ROUTES = ["/health", "/api/health", "/api/discovery/pending-pair", "/provision/status"]


@pytest.fixture(scope="module")
def gate_state(lan_client: httpx.Client) -> str:
    """'enforced' | 'open' | 'unreachable' for the direct LAN path."""
    try:
        r = lan_client.get("/api/status")
    except httpx.HTTPError:
        return "unreachable"
    if r.status_code == 403:
        try:
            if r.json().get("error") == "production_lan_refused":
                return "enforced"
        except ValueError:
            pass
    return "open"


def test_liveness_always_served_on_lan(lan_client, gate_state):
    if gate_state == "unreachable":
        pytest.skip("hub not directly reachable over LAN")
    for path in ("/health", "/api/health"):
        r = lan_client.get(path)
        assert r.status_code == 200, f"{path} must serve regardless of gate ({r.status_code})"


def test_setup_allowlist_served_on_lan(lan_client, gate_state):
    if gate_state == "unreachable":
        pytest.skip("hub not directly reachable over LAN")
    for path in ALLOWLIST_ROUTES:
        r = lan_client.get(path)
        assert r.status_code != 403, f"{path} is setup-allowlisted but got 403"


def test_production_routes_refused_on_lan(lan_client, gate_state):
    if gate_state == "unreachable":
        pytest.skip("hub not directly reachable over LAN")
    if gate_state == "open":
        pytest.skip("gate not enforced (setup mode or observe-only rollout)")
    for path in PRODUCTION_ROUTES:
        r = lan_client.get(path)
        assert r.status_code == 403, f"{path} served to direct LAN caller ({r.status_code})"
        body = r.json()
        assert body.get("error") == "production_lan_refused", body


def test_production_routes_served_via_loopback(hub_client, gate_state):
    """The sanctioned path (relay / loopback) must keep working."""
    if gate_state != "enforced":
        pytest.skip("gate not enforced — loopback parity covered by J1")
    for path in PRODUCTION_ROUTES:
        r = hub_client.get(path)
        assert r.status_code == 200, f"loopback {path} -> {r.status_code}"
