"""E2E fixtures — live hub HTTP only (Pi / LAN journeys)."""

from __future__ import annotations

import os

import httpx
import pytest

# hub_base_url, admin_auth, hub_client come from suites/conftest.py


@pytest.fixture(scope="session")
def lan_client(hub_base_url: str) -> httpx.Client:
    """Always-direct LAN client (no ssh-exec fallback) — used by the
    LAN-gate posture tests, which are about what a direct caller sees."""
    with httpx.Client(base_url=hub_base_url, timeout=15.0) as client:
        yield client


@pytest.fixture(scope="session")
def motion_entity_id() -> str:
    return os.environ.get("E2E_MOTION_ENTITY_ID", "").strip()
