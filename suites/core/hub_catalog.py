"""Load hub API catalog for parametrized live tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

SENTINEL_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = SENTINEL_ROOT / "contracts" / "hub_api_catalog.yaml"


def load_catalog_entries() -> list[dict[str, Any]]:
    data = yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8"))
    return list(data.get("endpoints", []))
