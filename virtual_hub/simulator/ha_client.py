"""Minimal Home Assistant REST client for twin sensor inject."""

from __future__ import annotations

from typing import Any

import httpx


class HAClient:
    def __init__(self, base_url: str, token: str, timeout: float = 30.0) -> None:
        self._base = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self._base,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            timeout=timeout,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> HAClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def set_state(
        self,
        entity_id: str,
        state: str,
        attributes: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"state": state}
        if attributes:
            body["attributes"] = attributes
        r = self._client.post(f"/api/states/{entity_id}", json=body)
        r.raise_for_status()
        return r.json()

    def get_state(self, entity_id: str) -> dict[str, Any]:
        r = self._client.get(f"/api/states/{entity_id}")
        r.raise_for_status()
        return r.json()
