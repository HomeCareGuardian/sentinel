"""Unit checks for CASAS → HA normaliser (no live hub required)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "virtual_hub" / "simulator"))

from casas_normaliser import event_to_ha_payload, normalise_scenario_events  # noqa: E402

pytestmark = [pytest.mark.functional]


def test_casas_motion_shorthand():
    payload = event_to_ha_payload({"sensor": "M001", "value": "ON", "offset_seconds": 5})
    assert payload["entity_id"].startswith("binary_sensor.vch_")
    assert payload["state"] == "on"
    assert payload["offset_seconds"] == 5


def test_explicit_entity_passthrough():
    payload = event_to_ha_payload(
        {
            "entity_id": "binary_sensor.vch_kitchen_motion",
            "state": "off",
            "attributes": {"device_class": "motion"},
        }
    )
    assert payload["entity_id"] == "binary_sensor.vch_kitchen_motion"
    assert payload["state"] == "off"


def test_scenario_batch():
    events = normalise_scenario_events(
        [
            {"sensor": "D001", "value": "OPEN"},
            {"sensor": "D001", "value": "CLOSE"},
        ]
    )
    assert len(events) == 2
    assert events[0]["state"] == "on"
    assert events[1]["state"] == "off"
