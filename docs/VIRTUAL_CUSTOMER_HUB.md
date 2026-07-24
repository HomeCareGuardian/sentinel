# Virtual Customer Hub (Digital Twin)

Always-on (or on-demand) test hub owned by **Sentinel**. It deploys **published**
product images and drives sensors through **Home Assistant REST**, then asserts
hub HTTP APIs black-box style.

## What it is

| Piece | Source |
|-------|--------|
| `hcg-core` | Published GHCR image (`HCG_IMAGE`) |
| Home Assistant | Published HA image (`HOME_ASSISTANT_VERSION`) |
| Postgres | `POSTGRES_IMAGE` (default `postgres:15`) |
| Day simulator | This repo (`virtual_hub/simulator`) |
| Functional tests | `suites/functional` (`pytest -m functional`) |

No hcg source checkout. No hub inject API. No `HCG_VIRTUAL_HUB` flag.

Image pins are intended to track **hcg multi-image OTA** (hub + HA + Postgres)
as that work lands in the product repo. Until then, bump pins in
`config/targets.virtual-hub.env` and run `./scripts/virtual-hub.sh pull` / `deploy`.

## Quick start (local Docker CLI)

Uses **`docker compose`**. Works with Docker Engine or Podman’s docker-compat
CLI (`docker version` shows “Podman Engine”).

```bash
cp config/targets.virtual-hub.env.example config/targets.virtual-hub.env
# Edit ADMIN_PASSWORD and set HCG_IMAGE if you do not use :latest

./scripts/virtual-hub.sh up
# Bootstraps HA (onboarding + HA_TOKEN), starts hub

./scripts/virtual-hub.sh run-scenario idle_home
./scripts/virtual-hub.sh run-tests
```

Optional continuous simulator:

```bash
VCH_SIM_MODE=continuous ./scripts/virtual-hub.sh up simulator
```

### Day-runner modes

The simulator (`virtual_hub/simulator/day_runner.py`) supports three modes via
`--mode` or `VCH_SIM_MODE`:

| Mode | Behaviour |
|------|-----------|
| `once` | Replay scenario once and exit (used by `run-scenario`) |
| `repeat` | Replay `--repeat N` times (`VCH_SIM_REPEAT`, default 1) |
| `continuous` | Loop forever; sleeps until next day boundary between runs |

`run-scenario` uses `--mode once --accelerated`. The `up simulator` profile sets
`VCH_SIM_MODE=continuous` in compose.

Override with `VCH_COMPOSE="docker compose"` only if you need a non-default path.
## How sensor inject works

1. Simulator POSTs to HA `http://homeassistant:8123/api/states/{entity_id}`
   with `HA_TOKEN` (long-lived access token).
2. Hub is configured with `HA_HOST=homeassistant` and the same token.
3. Hub websocket receives `state_changed` and runs the normal pipeline.
4. Functional tests call hub `GET /api/states`, `/health`, `/api/devices`, etc.

HA is bound to `127.0.0.1:8123` on the host for operator debug only. Do not
expose it on the public internet. The caregiver app never talks to HA.

## Commands

| Command | Purpose |
|---------|---------|
| `up` / `up simulator` | Start stack (optional day-simulator profile) |
| `down` | Stop containers (volumes kept) |
| `bootstrap-ha` | Onboard HA + write `HA_TOKEN` |
| `deploy [tag]` | Point `HCG_IMAGE` at a tag, pull, recreate hub |
| `pull` | Pull hub + HA + postgres pins |
| `wait-healthy` | Block until hub `/health` is OK |
| `run-scenario NAME` | Accelerated one-shot inject |
| `run-tests` | `pytest -m functional` against `HUB_BASE_URL` |

## Oracle

Versioned expectations live under `oracle/v0/`. Phase 1 covers response schema
and activity entity presence after scenarios. ML alert goldens are deferred.

## OCI Always Free

See [OCI_ALWAYS_FREE_RUNBOOK.md](OCI_ALWAYS_FREE_RUNBOOK.md) for hosting the
same compose stack on an Ampere VM and cronning the functional suite.

## Relation to Pi `pr-gate-hub`

Founder Pi flows (`./bin/sentinel --local pr-gate-hub`) are unchanged. The
virtual hub is an additional target profile (`targets.virtual-hub.env`).
