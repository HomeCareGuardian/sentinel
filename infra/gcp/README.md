# GCP E2E hub environment

Black-box tests do not provision GCP from this repo automatically yet. Use this guide to run a **dedicated E2E hub** on Compute Engine, then point `config/targets.gcp.env` at it.

## Architecture

```text
GitHub Actions (sentinel)  ──HTTPS──►  GCE VM (docker compose: postgres, HA, hcg-core)
                    └──HTTPS──►  Staging website (Workers / preview URL)
```

The E2E repo only needs reachable URLs — same tests as `--local`.

## 1. Create a VM (example)

```bash
export PROJECT_ID=core-dominion-481813-i8
export ZONE=europe-west2-a
export VM_NAME=sentinel-e2e-hub

gcloud compute instances create "${VM_NAME}" \
  --project="${PROJECT_ID}" \
  --zone="${ZONE}" \
  --machine-type=e2-standard-4 \
  --boot-disk-size=80GB \
  --tags=sentinel-e2e-hub \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud
```

Open **8080** (hub API) and **8123** (HA UI, optional) via firewall only from your IP or IAP — do not expose Postgres publicly.

## 2. Install hub stack on the VM

SSH in and deploy `hcg-core` the same way as a Pi (Docker Compose from the `hcg` product repo). Ensure:

- `GET http://<vm-ip>:8080/health` returns healthy
- Admin credentials match `ADMIN_*` in `targets.gcp.env`

## 3. Configure E2E repo

```bash
cp config/targets.gcp.env.example config/targets.gcp.env
# Edit HUB_BASE_URL (https if you terminate TLS on the VM or load balancer)
# Edit WEBSITE_BASE_URL to your staging site
```

## 4. Run tests

```bash
./bin/sentinel --gcp check-targets
./bin/sentinel --gcp pr-gate
```

## 5. GitHub Actions secrets (GCP profile)

In `HomeCareGuardian/sentinel` repository settings, add environment **`gcp`** or use secret names:

| Secret | Example |
|--------|---------|
| `E2E_GCP_HUB_BASE_URL` | `https://e2e-hub.yourdomain:8080` |
| `E2E_GCP_WEBSITE_BASE_URL` | `https://staging.homecareguardian.io` |
| `E2E_GCP_ADMIN_USERNAME` | |
| `E2E_GCP_ADMIN_PASSWORD` | |
| `E2E_GCP_USER_EMAIL` | |
| `E2E_GCP_USER_PASSWORD` | |

The workflow job `hub-e2e-gcp` maps these automatically (see `.github/workflows/e2e.yml`).

## Ephemeral VMs (optional)

For a fresh stack every run, wrap VM create → deploy → `sentinel --gcp pr-gate` → delete in a `hcg` deploy workflow or Terraform. Keep Terraform in the product/infra repo, not in sentinel, to preserve black-box isolation.
