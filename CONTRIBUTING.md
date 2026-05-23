# Contributing to Sentinel

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install httpx pytest pytest-timeout PyYAML requests

cp config/targets.local.env.example config/targets.local.env
```

## Run locally

```bash
./bin/sentinel --local --hub-host <your-hub-device-id> pr-gate-hub
```

## Add journeys

1. Add P0 paths to `contracts/endpoints.manifest.yaml` if needed.
2. Add tests under `suites/core/test_j*.py` using `hub_client` and `@pytest.mark.sentinel_e2e`.

## Publish

Create `https://github.com/HomeCareGuardian/sentinel` and push this directory. Configure CI secrets per `README.md`.
