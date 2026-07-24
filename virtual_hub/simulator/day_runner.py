#!/usr/bin/env python3
"""Replay a synthetic day of sensor events into Home Assistant via REST."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Literal

from casas_normaliser import normalise_scenario_events
from ha_client import HAClient

SimMode = Literal["once", "repeat", "continuous"]

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
    events.sort(key=lambda e: float(e.get("offset_seconds") or 0))
    speed = float(scenario.get("accelerated_speed") or 60.0) if accelerated else 1.0
    last_t = 0.0
    injected = 0
    for ev in events:
        t = float(ev.get("offset_seconds") or 0)
        delay = max(0.0, (t - last_t) / speed)
        if delay:
            if accelerated:
                time.sleep(min(delay, 0.05))
            else:
                time.sleep(delay)
        last_t = t
        client.set_state(ev["entity_id"], ev["state"], ev.get("attributes") or {})
        injected += 1
        print(f"injected {ev['entity_id']}={ev['state']} @+{t:.1f}s")
    return injected


def _sleep_until_next_day() -> None:
    sleep_s = max(60, 86400 - int(time.time()) % 86400)
    print(f"sleeping {sleep_s}s until next day boundary")
    time.sleep(sleep_s)


def run_mode(
    client: HAClient,
    scenario: dict[str, Any],
    *,
    scenario_name: str,
    mode: SimMode,
    repeat: int,
    accelerated: bool,
) -> int:
    if mode == "once":
        n = replay(client, scenario, accelerated=accelerated)
        print(f"done: {n} events from {scenario_name}")
        return 0

    if mode == "repeat":
        total = 0
        for run in range(1, repeat + 1):
            print(f"=== repeat {run}/{repeat} scenario={scenario_name} ===")
            total += replay(client, scenario, accelerated=accelerated)
        print(f"done: {total} events across {repeat} run(s) of {scenario_name}")
        return 0

    if mode == "continuous":
        day = 0
        while True:
            day += 1
            print(f"=== day {day} scenario={scenario_name} ===")
            replay(client, scenario, accelerated=accelerated)
            if not accelerated:
                _sleep_until_next_day()
        # unreachable

    raise ValueError(f"unknown simulator mode: {mode!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", default=os.environ.get("SCENARIO", "idle_home"))
    parser.add_argument(
        "--ha-url",
        default=os.environ.get("HA_BASE_URL", "http://homeassistant:8123"),
    )
    parser.add_argument("--token", default=os.environ.get("HA_TOKEN", ""))
    parser.add_argument(
        "--mode",
        choices=("once", "repeat", "continuous"),
        default=os.environ.get("VCH_SIM_MODE", "once"),
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=int(os.environ.get("VCH_SIM_REPEAT", "1")),
    )
    parser.add_argument(
        "--accelerated",
        action="store_true",
        default=os.environ.get("VCH_ACCELERATED") == "1",
    )
    args = parser.parse_args()

    if not args.token:
        print("HA_TOKEN is required", file=sys.stderr)
        return 2
    if args.mode == "repeat" and args.repeat < 1:
        print("--repeat must be >= 1", file=sys.stderr)
        return 2

    scenario = load_scenario(args.scenario)
    with HAClient(args.ha_url, args.token) as client:
        return run_mode(
            client,
            scenario,
            scenario_name=args.scenario,
            mode=args.mode,
            repeat=args.repeat,
            accelerated=args.accelerated,
        )


if __name__ == "__main__":
    raise SystemExit(main())
