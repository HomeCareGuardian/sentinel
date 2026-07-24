# OCI Always Free runbook — Virtual Customer Hub

Host the Sentinel digital twin on an Oracle Cloud Always Free Ampere (ARM)
VM so you can hit a standing hub remotely and cron functional tests without
burning GitHub Actions minutes every day.

## 1. VM

- Shape: `VM.Standard.A1.Flex` (Always Free Ampere), 2–4 OCPUs, 12–24 GB RAM
  as your tenancy allows.
- Image: Ubuntu 22.04/24.04 ARM64.
- Networking: public SSH (your IP only); **do not** open HA `8123` publicly.
  Optionally open hub `8080` only to the IP that runs Sentinel tests, or use
  an SSH tunnel.

## 2. Install Docker

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"
# log out/in
```

## 3. Clone Sentinel and configure

```bash
git clone https://github.com/HomeCareGuardian/sentinel.git
cd sentinel
cp config/targets.virtual-hub.env.example config/targets.virtual-hub.env
```

Set strong `ADMIN_PASSWORD`, and pin images to match the product release you
want under test (same pins hcg multi-image OTA will ship):

```bash
HCG_IMAGE=ghcr.io/homecareguardian/hcg-core:<tag>
HOME_ASSISTANT_VERSION=2026.6.4
POSTGRES_IMAGE=postgres:15
```

Authenticate to GHCR if the hub image is private (needs **package read** on
`hcg-core`, not only `gh auth login`):

```bash
echo "$GHCR_TOKEN" | docker login ghcr.io -u USERNAME --password-stdin
# or: podman login ghcr.io (same store when using docker-compat)
```

If pull returns `denied`, an org admin must grant your GitHub user read access
to the `hcg-core` container package.
## 4. Start the twin

```bash
./scripts/virtual-hub.sh up simulator
./scripts/virtual-hub.sh wait-healthy
```

Confirm from the VM:

```bash
curl -fsS http://127.0.0.1:8080/health
```

## 5. Firewall

- Allow TCP `22` from admin IPs.
- Allow TCP `8080` only from test runners (or rely on SSH local forward
  `ssh -L 8080:127.0.0.1:8080 ubuntu@vm`).
- Keep `8123` on localhost only (compose already binds `127.0.0.1:8123`).

## 6. Daily cron (standing twin)

```cron
# Inject a synthetic day and run functional suite; mail/log failures.
15 4 * * * cd /home/ubuntu/sentinel && ./scripts/virtual-hub.sh run-scenario single_day_motion >>/var/log/vch-sim.log 2>&1
30 4 * * * cd /home/ubuntu/sentinel && ./scripts/virtual-hub.sh run-tests >>/var/log/vch-test.log 2>&1
```

## 7. Updating images (align with OTA)

When hcg publishes a new coordinated pin set (hub / HA / Postgres):

```bash
./scripts/virtual-hub.sh deploy <new-hcg-tag>
# If HA or Postgres pins changed in targets.virtual-hub.env:
./scripts/virtual-hub.sh pull
./scripts/virtual-hub.sh up
```

Field hubs will receive the same pins via **multi-image OTA** (in progress in
hcg). The OCI twin is updated explicitly here until/unless the VM is enrolled
in that OTA channel.

## 8. systemd (optional)

Create a unit that runs `docker compose ... up -d` on boot so the twin
survives reboot. Prefer `restart: unless-stopped` already set on services.
