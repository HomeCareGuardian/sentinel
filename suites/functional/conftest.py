"""Virtual hub functional fixtures — oracle + hub version on shared hub client."""

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
