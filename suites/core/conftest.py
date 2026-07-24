"""E2E fixtures — live hub HTTP only."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from lib.hub_transport import make_hub_client  # noqa: E402


@pytest.fixture(scope="session")
def hub_base_url() -> str:
    url = os.environ.get("HUB_BASE_URL", "http://127.0.0.1:8080").rstrip("/")
    return url


@pytest.fixture(scope="session")
def hub_client(hub_base_url: str) -> httpx.Client:
    with make_hub_client() as client:
        yield client


@pytest.fixture(scope="session")
def lan_client(hub_base_url: str) -> httpx.Client:
    """Always-direct LAN client (no ssh-exec fallback) — used by the
    LAN-gate posture tests, which are about what a direct caller sees."""
    with httpx.Client(base_url=hub_base_url, timeout=15.0) as client:
        yield client


@pytest.fixture(scope="session")
def admin_auth() -> httpx.Auth | None:
    user = os.environ.get("ADMIN_USERNAME", "")
    password = os.environ.get("ADMIN_PASSWORD", "")
    if user and password:
        return httpx.BasicAuth(user, password)
    return None


@pytest.fixture(scope="session")
def motion_entity_id() -> str:
    return os.environ.get("E2E_MOTION_ENTITY_ID", "").strip()
