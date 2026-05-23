# Sentinel

Black-box live regression for [HomeCareGuardian](https://github.com/HomeCareGuardian) — hub, website, and iOS surfaces.

**Repository:** [github.com/HomeCareGuardian/sentinel](https://github.com/HomeCareGuardian/sentinel) (standalone; no product source in this tree).

## Quick start

```bash
cp config/targets.local.env.example config/targets.local.env
# Set HUB_HOST to your Pi device id (e.g. hcg-hub-5fcf7e73cfe7a329)

./bin/sentinel --local --hub-host hcg-hub-5fcf7e73cfe7a329 target
./bin/sentinel --local --hub-host hcg-hub-5fcf7e73cfe7a329 pr-gate-hub
```

Pi on your LAN (SSH + LAN probe + gate):

```bash
./scripts/run-local.sh --host hcg-hub-5fcf7e73cfe7a329
```

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
| `pr-gate-hub` | Hub-only P0 gate |
| `pr-gate` | Hub + website + iOS P0 |

## CI

See [`.github/workflows/e2e.yml`](.github/workflows/e2e.yml). GCP secrets: `E2E_GCP_HUB_BASE_URL`, etc. Local: `E2E_LOCAL_HUB_HOST` or `E2E_LOCAL_HUB_BASE_URL`.

## Principles

- Live HTTP/UI only — no mocks, no checkout of `hcg`, `Website`, or `iOS-App`.
- You provide deployed URLs; Sentinel probes them.
