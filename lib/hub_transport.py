"""Hub HTTP transport — direct LAN or SSH-exec loopback.

Hubs past setup mode refuse production API routes from direct LAN callers
(hcg#640 / hcg#2333: 403 ``production_lan_refused``); only loopback peers
(the relay-proxied path) are served. Hub SSH hardening also sets
``AllowTcpForwarding no``, so an ``ssh -L`` tunnel cannot reach loopback.

SSH *exec* is still allowed, so this module provides an httpx transport
that runs ``curl`` on the hub itself against ``http://127.0.0.1:8080``.
Requests keep full black-box HTTP semantics; only the wire path changes.
An SSH ControlMaster connection is reused across requests, so per-request
overhead is a few tens of milliseconds.

Selection (``HUB_TRANSPORT``):

* ``direct``    — plain httpx to ``HUB_BASE_URL``.
* ``ssh-exec``  — always go via ``ssh PI_HOST curl`` loopback.
* ``auto`` (default) — probe ``HUB_BASE_URL`` once; if a production route
  answers 403 ``production_lan_refused`` and ``PI_HOST`` is set, switch
  to ``ssh-exec``.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import tempfile

import httpx

DEFAULT_LOOPBACK_URL = "http://127.0.0.1:8080"
PROBE_PATH = "/api/status"  # production route: gated on LAN, served on loopback
GATE_ERROR = "production_lan_refused"

_CONTROL_DIR = os.path.join(tempfile.gettempdir(), "sentinel-ssh")


def _ssh_base_args() -> list[str]:
    os.makedirs(_CONTROL_DIR, exist_ok=True)
    return [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=10",
        "-o", "ControlMaster=auto",
        "-o", f"ControlPath={_CONTROL_DIR}/cm-%r@%h",
        "-o", "ControlPersist=300",
    ]


def _ssh_destination() -> str:
    host = os.environ.get("PI_HOST", "").strip()
    if not host:
        raise RuntimeError(
            "HUB_TRANSPORT=ssh-exec needs PI_HOST (hub SSH host); "
            "set HUB_HOST or PI_HOST in config/targets.local.env"
        )
    user = os.environ.get("HUB_SSH_USER", "pi").strip()
    return f"{user}@{host}"


class SSHExecTransport(httpx.BaseTransport):
    """Serve httpx requests by running curl on the hub over SSH exec."""

    def __init__(self, loopback_url: str | None = None, max_time: float = 60.0) -> None:
        self._loopback = (
            loopback_url
            or os.environ.get("HUB_LOOPBACK_URL", DEFAULT_LOOPBACK_URL)
        ).rstrip("/")
        self._dest = _ssh_destination()
        self._max_time = max(1, int(max_time))

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        url = self._loopback + request.url.raw_path.decode("ascii")
        curl = [
            "curl", "-sS", "--http1.1", "-D", "-",
            "--max-time", str(self._max_time),
            "-X", request.method,
            url,
        ]
        for name, value in request.headers.items():
            if name.lower() in ("host", "content-length", "connection", "accept-encoding"):
                continue
            curl += ["-H", f"{name}: {value}"]
        body = request.read()
        if body:
            curl += ["--data-binary", "@-"]

        cmd = _ssh_base_args() + [self._dest, " ".join(shlex.quote(a) for a in curl)]
        proc = subprocess.run(
            cmd, input=body, capture_output=True, timeout=self._max_time + 30, check=False
        )
        if proc.returncode != 0:
            raise httpx.TransportError(
                f"ssh-exec curl failed (rc={proc.returncode}): "
                f"{proc.stderr.decode(errors='replace')[:300]}"
            )
        return self._parse(proc.stdout, request)

    @staticmethod
    def _parse(raw: bytes, request: httpx.Request) -> httpx.Response:
        # curl -D - writes one or more header blocks (e.g. on 100-continue)
        # followed by the body. Take the last header block.
        status = 0
        headers: list[tuple[str, str]] = []
        rest = raw
        while True:
            head, sep, after = rest.partition(b"\r\n\r\n")
            if not sep:
                break
            lines = head.split(b"\r\n")
            if not lines or not lines[0].startswith(b"HTTP/"):
                break
            parts = lines[0].split(b" ", 2)
            status = int(parts[1])
            headers = []
            for line in lines[1:]:
                name, _, value = line.partition(b":")
                headers.append((name.decode().strip(), value.decode().strip()))
            rest = after
            if not (100 <= status < 200):
                break
        if status == 0:
            raise httpx.TransportError(
                f"ssh-exec: no HTTP status in curl output: {raw[:200]!r}"
            )
        headers = [
            (n, v)
            for n, v in headers
            if n.lower() not in ("transfer-encoding", "content-encoding", "content-length")
        ]
        return httpx.Response(
            status_code=status, headers=headers, content=rest, request=request
        )


def _lan_gate_active(base_url: str) -> bool:
    try:
        r = httpx.get(base_url.rstrip("/") + PROBE_PATH, timeout=10.0)
    except httpx.HTTPError:
        # Hub unreachable over LAN entirely — ssh-exec is the only way in.
        return bool(os.environ.get("PI_HOST", "").strip())
    if r.status_code != 403:
        return False
    try:
        return r.json().get("error") == GATE_ERROR
    except (json.JSONDecodeError, ValueError):
        return False


def resolve_transport_mode(base_url: str | None = None) -> str:
    """Return the effective transport mode: ``direct`` or ``ssh-exec``."""
    mode = os.environ.get("HUB_TRANSPORT", "auto").strip().lower()
    if mode in ("direct", "ssh-exec"):
        return mode
    if mode != "auto":
        raise RuntimeError(f"HUB_TRANSPORT must be auto|direct|ssh-exec, got {mode!r}")
    base_url = base_url or os.environ.get("HUB_BASE_URL", DEFAULT_LOOPBACK_URL)
    if _lan_gate_active(base_url) and os.environ.get("PI_HOST", "").strip():
        print(
            f"INFO: LAN gate active on {base_url} — using ssh-exec loopback "
            f"transport via {_ssh_destination()}",
            file=sys.stderr,
        )
        return "ssh-exec"
    return "direct"


def make_hub_client(timeout: float = 30.0, base_url: str | None = None) -> httpx.Client:
    """Client for the hub API honouring HUB_TRANSPORT (auto-detects the gate)."""
    base_url = (base_url or os.environ.get("HUB_BASE_URL", DEFAULT_LOOPBACK_URL)).rstrip("/")
    if resolve_transport_mode(base_url) == "ssh-exec":
        return httpx.Client(
            base_url=base_url, timeout=timeout,
            transport=SSHExecTransport(max_time=timeout),
        )
    return httpx.Client(base_url=base_url, timeout=timeout)
