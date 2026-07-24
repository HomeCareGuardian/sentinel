# Sentinel

Black-box live regression for [HomeCareGuardian](https://github.com/HomeCareGuardian) — hub, website, and iOS surfaces.

**Repository:** [github.com/HomeCareGuardian/sentinel](https://github.com/HomeCareGuardian/sentinel) (standalone; no product source in this tree).  
**Project board:** [Sentinel — Live Regression](https://github.com/orgs/HomeCareGuardian/projects/13)

## Quick start

```bash
cp config/targets.local.env.example config/targets.local.env
# Set HUB_HOST and ADMIN_* (see docs/run-local.md)

pip install -e ".[dev]"

./bin/sentinel --local --hub-host hcg-hub-5fcf7e73cfe7a329 target
./bin/sentinel --local --hub-host hcg-hub-5fcf7e73cfe7a329 pr-gate-hub
```

**Pi on your LAN** (SSH probe, config write, hub P0 gate):

```bash
./scripts/run-local.sh --host hcg-hub-5fcf7e73cfe7a329
```

See **[docs/run-local.md](docs/run-local.md)** for prerequisites, tunnels, and troubleshooting.

`HUB_HOST` without a dot becomes `http://<host>.local:8080` (mDNS).

## Hubs past setup mode (LAN gate)

Production hubs refuse direct-LAN API calls with 403 `production_lan_refused`
(hcg#640/#2333); only loopback callers (the relay path) are served, and hub
sshd hardening blocks `ssh -L` tunnels. Sentinel handles this transparently:
when the gate is detected (and `PI_HOST`/`HUB_HOST` gives it SSH access), every
request runs as `ssh pi@<hub> curl http://127.0.0.1:8080/...` over a persisted
SSH connection (`lib/hub_transport.py`). Force a mode with
`HUB_TRANSPORT=direct|ssh-exec|auto`. The gate itself is regression-tested by
journey J0.

## Profiles

| Profile | Use when | Config |
| ------- | -------- | ------ |
| `--local` | Pi / LAN hub + local website | `config/targets.local.env` |
| `--gcp` | Staging hub on GCE + staging site | `config/targets.gcp.env` |
| virtual hub | Digital twin (compose + published images) | `config/targets.virtual-hub.env` |

Optional `config/targets.env` overrides either profile.

**Virtual customer hub (twin):** see [docs/VIRTUAL_CUSTOMER_HUB.md](docs/VIRTUAL_CUSTOMER_HUB.md).
`./scripts/virtual-hub.sh up` pulls published `hcg-core` + HA + Postgres; the
simulator injects via HA REST (no hcg code changes).

## Commands

| Command | Description |
| ------- | ----------- |
| `target` | Print active URLs and report dir |
| `check-targets` | Wait for hub + website |
| `bootstrap` | Seed hub via public HTTP |
| `contract` | Manifest vs live OpenAPI + iOS endpoint drift check |
| `journeys` | Pytest P0/P1 (`--p0`, `--p1`) |
| `website` | Playwright `@p0` (or `--full`) |
| `ios` | Hub HTTP P0 checklist |
| `ios-xcuitest` | XCUITest phase 2 (macOS; optional) |
| `pr-gate-hub` | Hub-only P0 gate |
| `pr-gate` | Hub + website + iOS P0 |

## Documentation

| Doc | Topic |
| ----- | ------ |
| [docs/run-local.md](docs/run-local.md) | Pi / `run-local.sh` |
| [docs/CI_SECRETS.md](docs/CI_SECRETS.md) | GitHub Actions secrets |
| [docs/WEBSITE_P0.md](docs/WEBSITE_P0.md) | Playwright P0 scope |
| [docs/HUB_DEPENDENCIES.md](docs/HUB_DEPENDENCIES.md) | Hub fixes (#6, #7) |
| [docs/VIRTUAL_CUSTOMER_HUB.md](docs/VIRTUAL_CUSTOMER_HUB.md) | Digital twin / virtual hub |
| [docs/OCI_ALWAYS_FREE_RUNBOOK.md](docs/OCI_ALWAYS_FREE_RUNBOOK.md) | OCI host for standing twin |
| [infra/gcp/README.md](infra/gcp/README.md) | Staging VM |
| [suites/ios/README.md](suites/ios/README.md) | iOS HTTP + XCUITest |

## CI

[`.github/workflows/e2e.yml`](.github/workflows/e2e.yml) runs `pr-gate` per profile. Configure secrets per [docs/CI_SECRETS.md](docs/CI_SECRETS.md).

## Principles

- Live HTTP/UI only — no mocks, no checkout of `hcg`, `Website`, or `iOS-App` in default CI.
- You provide deployed URLs; Sentinel probes them.
- **500 is never a pass.** Any 500 fails the gate — that is the point of the gate.
- Red is information: known-red tests reference their product ticket in the
  assertion message (currently hcg#2505 body-parse crashes, hcg#2506 device
  config). They stay red until the hub fix ships; do not loosen the expectation.
