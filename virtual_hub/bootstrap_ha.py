#!/usr/bin/env python3
"""Bootstrap Home Assistant for the virtual customer hub.

Completes onboarding when needed and ensures a long-lived access token exists
for the day-simulator (HA REST inject). Writes HA_TOKEN into the env file.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_USER = "vch_admin"
DEFAULT_PASSWORD = "vch_ha_change_me"
DEFAULT_TOKEN_NAME = "sentinel-vch"


def _http(
    method: str,
    url: str,
    *,
    token: str | None = None,
    body: dict[str, Any] | None = None,
    timeout: float = 15.0,
) -> tuple[int, Any]:
    data = None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8") or "null"
            return resp.status, json.loads(raw)
    except HTTPError as exc:
        raw = exc.read().decode("utf-8") if exc.fp else ""
        try:
            parsed: Any = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            parsed = raw
        return exc.code, parsed
    except URLError as exc:
        raise RuntimeError(f"HA unreachable at {url}: {exc}") from exc


def wait_for_ha(base: str, timeout: int = 180) -> None:
    start = time.time()
    while time.time() - start < timeout:
        try:
            status, _ = _http("GET", f"{base}/api/", timeout=5)
            # 401 means HA is up but needs auth; 200 with onboarding similarly.
            if status in (200, 401):
                return
        except RuntimeError:
            pass
        # Onboarding endpoint is available before full API auth.
        try:
            status, _ = _http("GET", f"{base}/api/onboarding", timeout=5)
            if status == 200:
                return
        except RuntimeError:
            pass
        time.sleep(2)
    raise RuntimeError(f"Home Assistant not ready within {timeout}s ({base})")


def onboarding_done(base: str) -> bool:
    status, payload = _http("GET", f"{base}/api/onboarding")
    if status != 200:
        # Already past onboarding: endpoint often 401 once configured.
        return status == 401
    if isinstance(payload, list):
        # Empty list or all steps done.
        return len(payload) == 0 or all(
            isinstance(x, dict) and x.get("done") for x in payload
        )
    if isinstance(payload, dict):
        steps = payload.get("steps") or payload.get("onboarding") or []
        if isinstance(steps, list) and steps:
            return all(isinstance(x, dict) and x.get("done") for x in steps)
    return False


def complete_onboarding(base: str, username: str, password: str) -> str | None:
    """Create owner user. Returns refresh/access token if present in response."""
    status, payload = _http(
        "POST",
        f"{base}/api/onboarding/users",
        body={
            "client_id": f"{base}/",
            "name": "Virtual Hub Admin",
            "username": username,
            "password": password,
            "language": "en",
        },
    )
    if status not in (200, 201):
        # May already be completed.
        print(f"onboarding users: HTTP {status} {payload}", file=sys.stderr)
        return None
    if isinstance(payload, dict):
        auth = payload.get("auth_code") or payload.get("access_token")
        if isinstance(auth, str):
            return auth
    return None


def login_token(base: str, username: str, password: str) -> str:
    """Obtain a short-lived token via the token endpoint (password grant)."""
    # HA auth token endpoint expects form body for password grant.
    import urllib.parse

    form = urllib.parse.urlencode(
        {
            "grant_type": "password",
            "client_id": f"{base}/",
            "username": username,
            "password": password,
        }
    ).encode("utf-8")
    req = Request(
        f"{base}/auth/login_flow",
        data=json.dumps(
            {
                "client_id": f"{base}/",
                "handler": ["homeassistant", None],
                "redirect_uri": f"{base}/?auth_callback=1",
            }
        ).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=20) as resp:
            flow = json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"login_flow failed: {exc.read().decode()}") from exc

    flow_id = flow.get("flow_id")
    if not flow_id:
        raise RuntimeError(f"login_flow missing flow_id: {flow}")

    req2 = Request(
        f"{base}/auth/login_flow/{flow_id}",
        data=json.dumps(
            {
                "client_id": f"{base}/",
                "username": username,
                "password": password,
            }
        ).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req2, timeout=20) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"login_flow submit failed: {exc.read().decode()}") from exc

    code = result.get("result")
    if not code:
        raise RuntimeError(f"login_flow did not return auth code: {result}")

    req3 = Request(
        f"{base}/auth/token",
        data=urllib.parse.urlencode(
            {
                "grant_type": "authorization_code",
                "code": code,
                "client_id": f"{base}/",
            }
        ).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urlopen(req3, timeout=20) as resp:
            token_body = json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"auth/token failed: {exc.read().decode()}") from exc

    access = token_body.get("access_token")
    if not access:
        raise RuntimeError(f"no access_token in {token_body}")
    return str(access)


def create_long_lived_token(base: str, access_token: str, name: str) -> str:
    """Create LLAT via WebSocket auth API (REST has no public LLAT create)."""
    try:
        import websocket  # type: ignore
    except ImportError:
        # Fallback: reuse short-lived access token for twin (restart refreshes via bootstrap).
        print(
            "websocket-client not installed; using session access token as HA_TOKEN",
            file=sys.stderr,
        )
        return access_token

    ws_url = base.replace("http://", "ws://").replace("https://", "wss://") + "/api/websocket"
    ws = websocket.create_connection(ws_url, timeout=20)
    try:
        hello = json.loads(ws.recv())
        if hello.get("type") != "auth_required":
            raise RuntimeError(f"unexpected WS hello: {hello}")
        ws.send(json.dumps({"type": "auth", "access_token": access_token}))
        auth_ok = json.loads(ws.recv())
        if auth_ok.get("type") != "auth_ok":
            raise RuntimeError(f"WS auth failed: {auth_ok}")
        msg_id = 1
        ws.send(
            json.dumps(
                {
                    "id": msg_id,
                    "type": "auth/long_lived_access_token",
                    "client_name": name,
                    "lifespan": 3650,
                }
            )
        )
        while True:
            raw = json.loads(ws.recv())
            if raw.get("id") == msg_id:
                if not raw.get("success"):
                    raise RuntimeError(f"LLAT create failed: {raw}")
                token = raw.get("result")
                if not token:
                    raise RuntimeError(f"LLAT empty result: {raw}")
                return str(token)
    finally:
        ws.close()


def upsert_env_token(env_file: Path, token: str) -> None:
    env_file.parent.mkdir(parents=True, exist_ok=True)
    if not env_file.exists():
        example = env_file.with_name("targets.virtual-hub.env.example")
        if example.exists():
            env_file.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            env_file.write_text("HA_TOKEN=\n", encoding="utf-8")
    lines = env_file.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    seen = False
    for line in lines:
        if line.startswith("HA_TOKEN="):
            out.append(f"HA_TOKEN={token}")
            seen = True
        else:
            out.append(line)
    if not seen:
        out.append(f"HA_TOKEN={token}")
    env_file.write_text("\n".join(out) + "\n", encoding="utf-8")


def token_works(base: str, token: str) -> bool:
    status, _ = _http("GET", f"{base}/api/", token=token)
    return status == 200


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ha-url", default=os.environ.get("HA_BASE_URL", "http://127.0.0.1:8123"))
    parser.add_argument(
        "--env-file",
        default=os.environ.get(
            "VCH_ENV_FILE",
            str(Path(__file__).resolve().parents[1] / "config" / "targets.virtual-hub.env"),
        ),
    )
    parser.add_argument("--username", default=os.environ.get("HA_USERNAME", DEFAULT_USER))
    parser.add_argument("--password", default=os.environ.get("HA_PASSWORD", DEFAULT_PASSWORD))
    parser.add_argument("--write-token", action="store_true")
    args = parser.parse_args()

    base = args.ha_url.rstrip("/")
    env_path = Path(args.env_file)

    wait_for_ha(base)

    existing = os.environ.get("HA_TOKEN", "").strip()
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("HA_TOKEN=") and not existing:
                existing = line.split("=", 1)[1].strip()

    if existing and token_works(base, existing):
        print("HA_TOKEN already valid")
        return 0

    if not onboarding_done(base):
        print("Completing HA onboarding...")
        complete_onboarding(base, args.username, args.password)
        # Finish remaining onboarding steps best-effort (core config / integration).
        for step in ("core_config", "analytics", "integration"):
            _http("POST", f"{base}/api/onboarding/{step}", body={})

    print("Logging in to obtain access token...")
    access = login_token(base, args.username, args.password)
    print("Creating long-lived access token...")
    llat = create_long_lived_token(base, access, DEFAULT_TOKEN_NAME)

    if args.write_token:
        upsert_env_token(env_path, llat)
        print(f"Wrote HA_TOKEN to {env_path}")
    else:
        print(llat)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001 — CLI surface
        print(f"bootstrap_ha failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
