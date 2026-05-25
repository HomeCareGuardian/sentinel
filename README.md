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

## Profiles

| Profile | Use when | Config |
| ------- | -------- | ------ |
| `--local` | Pi / LAN hub + local website | `config/targets.local.env` |
| `--gcp` | Staging hub on GCE + staging site | `config/targets.gcp.env` |

Optional `config/targets.env` overrides either profile.

## Commands

| Command | Description |
| ------- | ----------- |
| `target` | Print active URLs and report dir |
| `check-targets` | Wait for hub + website |
| `bootstrap` | Seed hub via public HTTP |
| `contract` | Manifest vs live OpenAPI |
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
| [infra/gcp/README.md](infra/gcp/README.md) | Staging VM |
| [suites/ios/README.md](suites/ios/README.md) | iOS HTTP + XCUITest |

## CI

[`.github/workflows/e2e.yml`](.github/workflows/e2e.yml) runs `pr-gate` per profile. Configure secrets per [docs/CI_SECRETS.md](docs/CI_SECRETS.md).

## Principles

- Live HTTP/UI only — no mocks, no checkout of `hcg`, `Website`, or `iOS-App` in default CI.
- You provide deployed URLs; Sentinel probes them.
