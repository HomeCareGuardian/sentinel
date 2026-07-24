# Running Sentinel on a Pi (LAN)

Use `scripts/run-local.sh` when the hub runs on a Raspberry Pi on your network. The script probes reachability, writes `config/targets.local.env`, and runs the hub-only P0 gate (`pr-gate-hub`).

## Prerequisites

- **Python 3.11+** — the script creates `.venv` and installs pytest deps if missing
- **SSH access** to the Pi (`pi@<device>.local` by default, or `--ssh-user`)
- **Hub API** listening on the Pi at `127.0.0.1:8080` (Docker / hcg-core)
- **LAN or tunnel** — mDNS (`*.local`) or SSH port-forward

Copy config once:

```bash
cp config/targets.local.env.example config/targets.local.env
```

Set `ADMIN_USERNAME` and `ADMIN_PASSWORD` to match `~/hcg-core/.env` on the Pi so J4 (anomaly acknowledge) runs instead of skipping. See [Pi admin credentials](#admin-credentials-j4).

## Quick run

```bash
./scripts/run-local.sh --host hcg-hub-5fcf7e73cfe7a329
```

Equivalent:

```bash
HUB_HOST=hcg-hub-5fcf7e73cfe7a329 ./scripts/run-local.sh
```

`HUB_HOST` without a dot resolves to `http://<host>.local:8080` (see `lib/resolve_hub_host.sh`).

## Options

| Flag | Purpose |
|------|---------|
| `--host <id>` | Pi device id (e.g. `hcg-hub-5fcf7e73cfe7a329`) |
| `--ssh-user <user>` | SSH user (default: `pi`) |
| `--ssh-tunnel` | Deprecated. `-L` forwarding is blocked on hardened hubs (`AllowTcpForwarding no`), so this now just sets `HUB_TRANSPORT=ssh-exec` (loopback transport) instead of opening a dead tunnel |

`--ssh-tunnel` no longer starts an `ssh -L` tunnel. On hubs past setup mode the sshd config refuses port forwarding, so the flag is routed to the `ssh-exec` loopback transport (curl on the Pi against `127.0.0.1:8080`). If you are on the Pi LAN you do not need the flag at all: the suites auto-detect the LAN gate and switch to `ssh-exec` themselves.

```bash
./scripts/run-local.sh --host hcg-hub-5fcf7e73cfe7a329 --ssh-tunnel
```

## What the script does

1. SSH to the Pi and `curl` `http://127.0.0.1:8080/health`
2. Unless `--ssh-tunnel` (which selects the `ssh-exec` loopback transport), probe `HUB_BASE_URL/health` on the LAN and detect the LAN gate
3. Update `config/targets.local.env` with `HUB_HOST`, `HUB_BASE_URL`, `PI_HOST`, `HUB_DEVICE_ID`
4. Verify `ADMIN_USERNAME` / `ADMIN_PASSWORD` are set (not placeholders)
5. Run `./bin/sentinel --local pr-gate-hub` (contract, bootstrap, pytest J1–J4, hub HTTP iOS smoke)

## GCP vs Pi LAN

| Profile | Config | When to use |
|---------|--------|-------------|
| `--local` | `config/targets.local.env` | Pi on LAN, local website dev server |
| `--gcp` | `config/targets.gcp.env` | Staging hub on GCE + staging website |

Pi teams normally use **`run-local.sh`** (local profile). CI and staging use **`--gcp`** — see [CI_SECRETS.md](CI_SECRETS.md).

Manual local gate without the script:

```bash
./bin/sentinel --local --hub-host hcg-hub-5fcf7e73cfe7a329 pr-gate-hub
```

Full merge gate (hub + website + iOS HTTP) requires a reachable `WEBSITE_BASE_URL`:

```bash
./bin/sentinel --local pr-gate
```

## Admin credentials (J4)

J4 posts to `/api/anomalies/{id}/acknowledge` with HTTP basic auth (`ADMIN_USERNAME` / `ADMIN_PASSWORD`).

On the Pi:

```bash
ssh pi@hcg-hub-<device-id>.local
grep '^ADMIN_' ~/hcg-core/.env
```

Copy those values into `config/targets.local.env`. Restart the hub stack if you change them.

Optional motion entity (J3): set `E2E_MOTION_ENTITY_ID` only if that entity exists in Home Assistant on the hub; otherwise leave it empty.

## Troubleshooting

| Symptom | Likely cause | What to try |
|---------|----------------|-------------|
| `FAIL: ssh … or Pi /health` | SSH key, hostname, hub down | `ssh pi@<PI_HOST>`, restart compose on Pi |
| `FAIL: not reachable` (LAN) | Wrong network, firewall, mDNS | `--ssh-tunnel`, ping `<host>.local` |
| `ModuleNotFoundError: suites` | Editable install missing | `pip install -e ".[dev]"` from repo root |
| J3 skipped | `E2E_MOTION_ENTITY_ID` not on hub | Unset var or provision entity in HA |
| J4 skipped | Admin auth not configured | Sync `ADMIN_*` from Pi `hcg-core/.env` |
| Contract warns on OpenAPI | `/openapi.json` returns 500 | Hub fix — see [HUB_DEPENDENCIES.md](HUB_DEPENDENCIES.md) |
| ML catalog allows 500 | ML stack unhealthy on Pi | Hub fix — same doc |

## Reports

JUnit and summaries land under `reports/local/` (e.g. `core-junit.xml`, `junit-merged.xml` after `pr-gate-hub`).
