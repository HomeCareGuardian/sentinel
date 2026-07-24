# CI secrets and staging targets

Sentinel CI runs live black-box tests against **deployed** hub and website URLs. No product repos are checked out in the workflow.

Workflow: [`.github/workflows/e2e.yml`](../.github/workflows/e2e.yml)  
GCP VM guide: [`infra/gcp/README.md`](../infra/gcp/README.md)

## Profiles

| Matrix profile | Generated config | Typical use |
|----------------|----------------|-------------|
| `gcp` | `config/targets.gcp.env` | Staging hub (GCE) + staging website |
| `local` | `config/targets.local.env` | Org LAN hub + website (optional second matrix job) |

Enable both on every PR/push:

```text
Repository variable: E2E_CI_LOCAL_ENABLED = true
```

## Virtual hub smoke

Workflow: [`.github/workflows/virtual-hub.yml`](../.github/workflows/virtual-hub.yml)

| Secret / variable | Purpose |
|-------------------|---------|
| `GHCR_READ_TOKEN` | **Required** for twin stack smoke — pull `ghcr.io/homecareguardian/hcg-core` |
| `VCH_STACK_SMOKE_ENABLED` | Repository **variable** (`true`) — run stack job on PRs (default: unit-only) |

Stack job sets `VCH_REQUIRE_SCENARIO=1` so functional tests **fail** if scenario
entities are missing on `/api/states`. Local opt-out: `VCH_ALLOW_MISSING_SCENARIO=1`.

Path-filtered on twin files; also `workflow_dispatch`. No daily GitHub schedule —
use OCI cron for standing twin (see `docs/OCI_ALWAYS_FREE_RUNBOOK.md`).

## Required GitHub secrets

### GCP profile (`gcp`)

| Secret | Maps to | Required |
|--------|---------|----------|
| `E2E_GCP_HUB_BASE_URL` | `HUB_BASE_URL` | Yes |
| `E2E_GCP_WEBSITE_BASE_URL` | `WEBSITE_BASE_URL` | Yes |
| `E2E_GCP_ADMIN_USERNAME` | `ADMIN_USERNAME` | Recommended (J4) |
| `E2E_GCP_ADMIN_PASSWORD` | `ADMIN_PASSWORD` | Recommended (J4) |
| `E2E_GCP_USER_EMAIL` | `E2E_USER_EMAIL` | Recommended (bootstrap) |
| `E2E_GCP_USER_PASSWORD` | `E2E_USER_PASSWORD` | Recommended (bootstrap) |

### Local profile (`local`) — optional matrix

| Secret | Maps to | Required |
|--------|---------|----------|
| `E2E_LOCAL_HUB_BASE_URL` **or** `E2E_LOCAL_HUB_HOST` | Hub target | Yes (one of) |
| `E2E_LOCAL_WEBSITE_BASE_URL` | `WEBSITE_BASE_URL` | Yes |
| `E2E_LOCAL_ADMIN_USERNAME` | `ADMIN_USERNAME` | Recommended |
| `E2E_LOCAL_ADMIN_PASSWORD` | `ADMIN_PASSWORD` | Recommended |
| `E2E_LOCAL_USER_EMAIL` | `E2E_USER_EMAIL` | Recommended |
| `E2E_LOCAL_USER_PASSWORD` | `E2E_USER_PASSWORD` | Recommended |

`E2E_LOCAL_HUB_HOST` uses the same mDNS rules as `HUB_HOST` (see `lib/resolve_hub_host.sh`).

## Staging provisioning (ops)

1. Deploy hub on GCE (or use an existing staging hub) — [`infra/gcp/README.md`](../infra/gcp/README.md).
2. Ensure `GET <HUB_BASE_URL>/health` is healthy and admin creds match secrets.
3. Point `E2E_GCP_WEBSITE_BASE_URL` at the staging marketing/care site (Vercel preview or staging host).
4. Add secrets under **Settings → Secrets and variables → Actions** for `HomeCareGuardian/sentinel`.
5. Run **Actions → Sentinel → Run workflow** with profile `gcp` to validate.

Once secrets are set, CI writes `config/targets.<profile>.env` automatically — no manual injection per run.

## Workflow behavior

- **Pull request / push to `main`:** runs `pr-gate` for each matrix profile. If required secrets for a profile are missing, the job **fails** with a clear message (avoids silent green skips).
- **Manual `workflow_dispatch`:** choose `gcp`, `local`, or `both`.

## Rotation

| Secret class | Rotation |
|--------------|----------|
| Admin (`E2E_*_ADMIN_*`) | Rotate on hub VM/Pi in `hcg-core/.env`, then update GitHub secrets |
| Caregiver test user | Re-register via bootstrap or hub admin; update `E2E_*_USER_*` |
| URLs | Update when staging VM or website host changes |

## What CI runs (`pr-gate`)

1. Wait for hub + website  
2. Contract check (manifest / OpenAPI)  
3. Bootstrap (caregiver + seed anomaly)  
4. Pytest P0 (J1–J4 + API catalog)  
5. Playwright `@p0` website specs  
6. iOS hub HTTP smoke (`suites/ios/run_hub_e2e.py`)  
7. Merge JUnit under `reports/<profile>/`

XCUITest phase 2 is **not** in default CI (macOS + app checkout). See [`suites/ios/README.md`](../suites/ios/README.md).

## Local parity

```bash
cp config/targets.gcp.env.example config/targets.gcp.env
# edit URLs and credentials
pip install -e ".[dev]"
./bin/sentinel --gcp pr-gate
```
