#!/usr/bin/env python3
"""Replay a synthetic day of sensor events into Home Assistant via REST."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from casas_normaliser import normalise_scenario_events
from ha_client import HAClient

SCENARIO_DIRS = [
    Path("/scenarios"),
    Path(__file__).resolve().parent / "scenarios",
]


def load_scenario(name: str) -> dict[str, Any]:
    for base in SCENARIO_DIRS:
        path = base / f"{name}.json"
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    raise FileNotFoundError(f"scenario not found: {name} (searched {SCENARIO_DIRS})")


def replay(
    client: HAClient,
    scenario: dict[str, Any],
    *,
    accelerated: bool,
) -> int:
    events = normalise_scenario_events(scenario.get("events") or [])
    # Sort by offset so chronological order is preserved.
    events.sort(key=lambda e: float(e.get("offset_seconds") or 0))
    speed = float(scenario.get("accelerated_speed") or 60.0) if accelerated else 1.0
    last_t = 0.0
    injected = 0
    for ev in events:
        t = float(ev.get("offset_seconds") or 0)
        delay = max(0.0, (t - last_t) / speed)
        if delay and not accelerated:
            time.sleep(delay)
        elif delay and accelerated:
            time.sleep(min(delay, 0.05))
        last_t = t
        client.set_state(ev["entity_id"], ev["state"], ev.get("attributes") or {})
        injected += 1
        print(f"injected {ev['entity_id']}={ev['state']} @+{t:.1f}s")
    return injected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", default=os.environ.get("SCENARIO", "idle_home"))
    parser.add_argument("--ha-url", default=os.environ.get("HA_BASE_URL", "http://homeassistant:8123"))
    parser.add_argument("--token", default=os.environ.get("HA_TOKEN", ""))
    parser.add_argument("--accelerated", action="store_true", default=os.environ.get("ACCELERATED") == "1")
    parser.add_argument("--once", action="store_true", help="Run one scenario then exit")
    parser.add_argument("--loop-days", type=int, default=int(os.environ.get("LOOP_DAYS", "1")))
    args = parser.parse_args()

    if not args.token:
        print("HA_TOKEN is required", file=sys.stderr)
        return 2

    scenario = load_scenario(args.scenario)
    with HAClient(args.ha_url, args.token) as client:
        if args.once or args.loop_days <= 0:
            n = replay(client, scenario, accelerated=args.accelerated)
            print(f"done: {n} events from {args.scenario}")
            return 0

        day = 0
        while args.loop_days == 0 or day < args.loop_days:
            day += 1
            print(f"=== day {day} scenario={args.scenario} ===")
            replay(client, scenario, accelerated=args.accelerated)
            if args.loop_days == 1 and not args.accelerated:
                # Idle until next calendar day for continuous twin.
                sleep_s = max(60, 86400 - int(time.time()) % 86400)
                print(f"sleeping {sleep_s}s until next day boundary")
                time.sleep(sleep_s)
            elif day < args.loop_days:
                time.sleep(1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
