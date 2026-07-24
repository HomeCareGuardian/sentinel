"""Black-box functional suite against a live virtual customer hub."""

from __future__ import annotations

import os
from typing import Any

import httpx
import pytest

pytestmark = [pytest.mark.functional, pytest.mark.requires_virtual_hub]


@pytest.fixture(autouse=True)
def _require_hub_healthy(hub_base_url: str, request: pytest.FixtureRequest) -> None:
    if request.node.get_closest_marker("requires_virtual_hub") is None:
        return
    try:
        with httpx.Client(base_url=hub_base_url, timeout=5.0) as client:
            r = client.get("/health")
            if r.status_code != 200:
                pytest.skip(f"virtual hub not healthy at {hub_base_url}")
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"virtual hub unreachable at {hub_base_url}: {exc}")


def _entity_ids(payload: Any) -> set[str]:
    if isinstance(payload, list):
        return {
            x.get("entity_id")
            for x in payload
            if isinstance(x, dict) and x.get("entity_id")
        }
    if isinstance(payload, dict):
        if "states" in payload and isinstance(payload["states"], list):
            return _entity_ids(payload["states"])
        return {k for k in payload if isinstance(k, str) and "." in k}
    return set()


def _enforce_scenario_entities(
    *,
    ids: set[str],
    must_ids: list[str],
    must_sub: list[str],
    scenario: str,
) -> None:
    """Fail closed on missing scenario entities unless explicitly allowed to skip."""
    missing = [e for e in must_ids if e not in ids]
    sub_ok = not must_sub or any(any(s in eid for s in must_sub) for eid in ids)
    if not missing and sub_ok:
        return
    allow_skip = os.environ.get("VCH_ALLOW_MISSING_SCENARIO") == "1"
    require = os.environ.get("VCH_REQUIRE_SCENARIO") == "1"
    if allow_skip and not require:
        pytest.skip(
            f"scenario {scenario!r} entities not present (VCH_ALLOW_MISSING_SCENARIO=1); "
            "run: ./scripts/virtual-hub.sh run-scenario "
            f"{scenario}"
        )
    if missing:
        assert not missing, (
            f"scenario {scenario!r} missing entities {missing}; "
            "run: ./scripts/virtual-hub.sh run-scenario "
            f"{scenario}"
        )
    if must_sub and not sub_ok:
        assert sub_ok, (
            f"scenario {scenario!r}: no /api/states entity matches {must_sub}; "
            "run: ./scripts/virtual-hub.sh run-scenario "
            f"{scenario}"
        )


def test_health_matches_oracle(hub_client, oracle, hub_version):
    print(f"hub_version={hub_version}")
    spec = oracle["endpoints"]["GET /health"]
    r = hub_client.get("/health")
    assert r.status_code == spec["status"]
    data = r.json()
    for key in spec.get("required_keys") or []:
        assert key in data
    allowed = {s.lower() for s in (spec.get("status_values_any_of") or [])}
    if allowed:
        assert str(data.get("status", "")).lower() in allowed


def test_api_health(hub_client, oracle):
    spec = oracle["endpoints"]["GET /api/health"]
    r = hub_client.get("/api/health")
    assert r.status_code == spec["status"]


def test_api_status_shape(hub_client, oracle):
    spec = oracle["endpoints"]["GET /api/status"]
    r = hub_client.get("/api/status")
    assert r.status_code == spec["status"]
    data = r.json()
    assert isinstance(data, dict)
    any_keys = spec.get("required_any_keys") or []
    assert any(k in data for k in any_keys), f"expected one of {any_keys} in {list(data)[:20]}"


def test_api_devices_shape(hub_client, oracle):
    spec = oracle["endpoints"]["GET /api/devices"]
    r = hub_client.get("/api/devices")
    assert r.status_code == spec["status"], r.text[:300]
    data = r.json()
    for key in spec.get("required_keys") or []:
        assert key in data
    assert isinstance(data["devices"], list)


def test_states_after_idle_or_motion(hub_client, oracle):
    """After virtual-hub.sh run-scenario, synthetic entities appear on /api/states."""
    spec = oracle["endpoints"]["GET /api/states"]
    r = hub_client.get("/api/states")
    assert r.status_code == spec["status"], r.text[:300]
    ids = {i for i in _entity_ids(r.json()) if i}
    scenario = os.environ.get("VCH_SCENARIO", "idle_home")
    after = (spec.get("after_scenario") or {}).get(scenario) or {}
    must_ids = after.get("must_include_entity_ids") or []
    must_sub = after.get("must_include_entity_substrings") or []
    if must_ids or must_sub:
        _enforce_scenario_entities(
            ids=ids,
            must_ids=must_ids,
            must_sub=must_sub,
            scenario=scenario,
        )
