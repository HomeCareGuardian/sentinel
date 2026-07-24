"""Shared Sentinel pytest fixtures (hub HTTP)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib.hub_transport import make_hub_client  # noqa: E402


@pytest.fixture(scope="session")
def hub_base_url() -> str:
    return os.environ.get("HUB_BASE_URL", "http://127.0.0.1:8080").rstrip("/")


@pytest.fixture(scope="session")
def admin_auth() -> httpx.Auth | None:
    user = os.environ.get("ADMIN_USERNAME", "")
    password = os.environ.get("ADMIN_PASSWORD", "")
    if user and password:
        return httpx.BasicAuth(user, password)
    return None


@pytest.fixture(scope="session")
def hub_client(hub_base_url: str, admin_auth: httpx.Auth | None) -> httpx.Client:
    """Hub API client via make_hub_client (HUB_TRANSPORT=auto|direct|ssh-exec)."""
    with make_hub_client(base_url=hub_base_url) as client:
        if admin_auth is not None:
            client.auth = admin_auth
        yield client
