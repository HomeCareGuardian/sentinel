# Contributing to Sentinel

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp config/targets.local.env.example config/targets.local.env
# Edit HUB_HOST, ADMIN_* (match Pi ~/hcg-core/.env for LAN runs)
```

## Run locally

**Pi / LAN (recommended):**

```bash
./scripts/run-local.sh --host <hcg-hub-device-id>
```

**Manual:**

```bash
./bin/sentinel --local --hub-host <device-id> pr-gate-hub
./bin/sentinel --gcp pr-gate    # needs config/targets.gcp.env
```

See [docs/run-local.md](docs/run-local.md) and [docs/CI_SECRETS.md](docs/CI_SECRETS.md).

## Add hub journeys

1. Add P0 paths to `contracts/endpoints.manifest.yaml` if needed.
2. Add tests under `suites/core/test_j*.py` with `@pytest.mark.sentinel_e2e`.
3. Register in `journeys/catalog.yaml`.

## Website / iOS

- Website P0: `suites/website/e2e/` — [docs/WEBSITE_P0.md](docs/WEBSITE_P0.md)
- iOS phase 1 (HTTP): `suites/ios/run_hub_e2e.py`
- iOS phase 2 (XCUITest): [suites/ios/README.md](suites/ios/README.md)

## Hub blockers

OpenAPI and ML endpoint failures are tracked in [docs/HUB_DEPENDENCIES.md](docs/HUB_DEPENDENCIES.md) until fixed in the hub product repo.
