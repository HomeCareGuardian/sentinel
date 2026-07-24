"""Virtual hub functional fixtures — live HTTP against HUB_BASE_URL."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx
import pytest

ORACLE_PATH = (
    Path(__file__).resolve().parents[2] / "oracle" / "v0" / "schema_activity.json"
)


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
    with httpx.Client(base_url=hub_base_url, timeout=30.0, auth=admin_auth) as client:
        yield client


@pytest.fixture(scope="session")
def oracle() -> dict[str, Any]:
    return json.loads(ORACLE_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def hub_version(hub_client: httpx.Client) -> str:
    """Capture hub version string for the report (best-effort)."""
    for path in ("/api/status", "/health", "/api/health"):
        try:
            r = hub_client.get(path)
            if r.status_code != 200:
                continue
            data = r.json()
            if not isinstance(data, dict):
                continue
            for key in ("version", "hub_version", "software_version", "build"):
                if key in data and data[key]:
                    return str(data[key])
            comps = data.get("components")
            if isinstance(comps, dict) and comps.get("version"):
                return str(comps["version"])
        except Exception:
            continue
    return os.environ.get("HCG_IMAGE", "unknown")
