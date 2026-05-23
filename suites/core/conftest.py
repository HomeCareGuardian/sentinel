"""E2E fixtures — live hub HTTP only."""

from __future__ import annotations

import os

import httpx
import pytest


@pytest.fixture(scope="session")
def hub_base_url() -> str:
    url = os.environ.get("HUB_BASE_URL", "http://127.0.0.1:8080").rstrip("/")
    return url


@pytest.fixture(scope="session")
def hub_client(hub_base_url: str) -> httpx.Client:
    with httpx.Client(base_url=hub_base_url, timeout=30.0) as client:
        yield client


@pytest.fixture(scope="session")
def admin_auth() -> httpx.Auth | None:
    user = os.environ.get("ADMIN_USERNAME", "e2e_admin")
    password = os.environ.get("ADMIN_PASSWORD", "e2e_admin_password")
    if user and password:
        return httpx.BasicAuth(user, password)
    return None


@pytest.fixture(scope="session")
def motion_entity_id() -> str:
    return os.environ.get("E2E_MOTION_ENTITY_ID", "").strip()
