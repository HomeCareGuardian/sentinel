"""Normalise CASAS-like / synthetic events into HA REST state payloads."""

from __future__ import annotations

from typing import Any, Iterable


def event_to_ha_payload(event: dict[str, Any]) -> dict[str, Any]:
    """Map one scenario event to HA set_state arguments.

    Accepted shapes:
      {"entity_id": "binary_sensor.x", "state": "on", "attributes": {...}}
      {"sensor": "M001", "value": "ON", "ts": "..."}  # CASAS-like shorthand
    """
    if "entity_id" in event and "state" in event:
        return {
            "entity_id": str(event["entity_id"]),
            "state": str(event["state"]),
            "attributes": dict(event.get("attributes") or {}),
            "offset_seconds": float(event.get("offset_seconds") or 0),
        }

    sensor = str(event.get("sensor") or event.get("device") or "").strip()
    value = str(event.get("value") or event.get("state") or "").strip()
    if not sensor or not value:
        raise ValueError(f"unrecognised event shape: {event!r}")

    entity_id = casas_sensor_to_entity(sensor)
    state = normalise_binary_state(value)
    attrs = {
        "friendly_name": sensor,
        "source": "sentinel-vch",
        "device_class": guess_device_class(sensor),
    }
    return {
        "entity_id": entity_id,
        "state": state,
        "attributes": attrs,
        "offset_seconds": float(event.get("offset_seconds") or event.get("t") or 0),
    }


def casas_sensor_to_entity(sensor: str) -> str:
    key = sensor.upper()
    if key.startswith("M") or "MOTION" in key:
        return f"binary_sensor.vch_{sensor.lower()}_motion"
    if key.startswith("D") or "DOOR" in key:
        return f"binary_sensor.vch_{sensor.lower()}_door"
    return f"sensor.vch_{sensor.lower()}"


def normalise_binary_state(value: str) -> str:
    v = value.strip().upper()
    if v in {"ON", "OPEN", "TRUE", "1", "PRESENT", "DETECTED"}:
        return "on"
    if v in {"OFF", "CLOSE", "CLOSED", "FALSE", "0", "ABSENT", "CLEAR"}:
        return "off"
    return value.lower()


def guess_device_class(sensor: str) -> str:
    key = sensor.upper()
    if key.startswith("M") or "MOTION" in key:
        return "motion"
    if key.startswith("D") or "DOOR" in key:
        return "door"
    return "occupancy"


def normalise_scenario_events(events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [event_to_ha_payload(e) for e in events]
