#!/usr/bin/env bash
# Pi LAN runner: SSH probe + write targets.local.env + pr-gate-hub.
#
#   ./scripts/run-local.sh --host hcg-hub-5fcf7e73cfe7a329
#   HUB_HOST=hcg-hub-5fcf7e73cfe7a329 ./scripts/run-local.sh
#
# Full guide: docs/run-local.md
set -euo pipefail

SENTINEL_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
USE_TUNNEL=false
HUB_HOST="${HUB_HOST:-}"
PI_USER="${HUB_SSH_USER:-pi}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ssh-tunnel) USE_TUNNEL=true; shift ;;
    --host) HUB_HOST="$2"; shift 2 ;;
    --ssh-user) PI_USER="$2"; shift 2 ;;
    *)
      echo "Unknown option: $1" >&2
      echo "Usage: $0 --host hcg-hub-<device-id> [--ssh-tunnel] [--ssh-user pi]" >&2
      exit 1
      ;;
  esac
done

if [[ -z "${HUB_HOST}" ]]; then
  echo "FAIL: set --host or HUB_HOST (e.g. hcg-hub-5fcf7e73cfe7a329)" >&2
  exit 1
fi

export HUB_HOST
# shellcheck source=/dev/null
source "${SENTINEL_ROOT}/lib/resolve_hub_host.sh"
hub_host_apply
export PI_USER

echo "==> Hub target: ${HUB_HOST}"
echo "    ssh:      ${PI_USER}@${PI_HOST}"
echo "    api:      ${HUB_BASE_URL}"
echo "    example:  ${HUB_BASE_URL}/api/devices"

echo "==> SSH + on-Pi health"
if ! ssh -o BatchMode=yes -o ConnectTimeout=15 "${PI_USER}@${PI_HOST}" \
  "curl -sf http://127.0.0.1:8080/health"; then
  echo "FAIL: ssh ${PI_USER}@${PI_HOST} or Pi /health" >&2
  exit 1
fi

TUNNEL_PID=""
cleanup() {
  [[ -n "${TUNNEL_PID}" ]] && kill "${TUNNEL_PID}" 2>/dev/null || true
}
trap cleanup EXIT

if [[ "${USE_TUNNEL}" == true ]]; then
  LOCAL_PORT="${E2E_LOCAL_PORT:-18080}"
  HUB_BASE_URL="http://127.0.0.1:${LOCAL_PORT}"
  ssh -N -o ExitOnForwardFailure=yes -L "${LOCAL_PORT}:127.0.0.1:8080" "${PI_USER}@${PI_HOST}" &
  TUNNEL_PID=$!
  sleep 2
else
  echo "==> LAN probe: ${HUB_BASE_URL}/health"
  if ! curl -sf "${HUB_BASE_URL}/health" >/dev/null; then
    echo "FAIL: not reachable — join the Pi LAN (hub sshd disallows -L tunnels)" >&2
    exit 1
  fi
  # Hubs past setup mode refuse production routes on the LAN (hcg#640/#2333);
  # the suites detect that and switch to the ssh-exec loopback transport.
  gate_probe="$(curl -s --max-time 10 "${HUB_BASE_URL}/api/status" || true)"
  if echo "${gate_probe}" | grep -q production_lan_refused; then
    echo "==> LAN gate enforced — suites will use ssh-exec loopback via ${PI_USER}@${PI_HOST}"
  else
    echo "==> LAN gate not enforced (setup mode) — direct HTTP"
  fi
fi

TARGETS_FILE="${SENTINEL_ROOT}/config/targets.local.env"
[[ -f "${TARGETS_FILE}" ]] || cp "${SENTINEL_ROOT}/config/targets.local.env.example" "${TARGETS_FILE}"
grep -vE '^(HUB_HOST|HUB_BASE_URL|PI_HOST|HUB_DEVICE_ID)=' "${TARGETS_FILE}" > "${TARGETS_FILE}.tmp" || true
{
  cat "${TARGETS_FILE}.tmp"
  echo "HUB_HOST=${HUB_HOST}"
  echo "HUB_BASE_URL=${HUB_BASE_URL}"
  echo "PI_HOST=${PI_HOST}"
  echo "HUB_DEVICE_ID=${HUB_DEVICE_ID}"
} > "${TARGETS_FILE}"
rm -f "${TARGETS_FILE}.tmp"

export HUB_HOST HUB_BASE_URL PI_HOST HUB_DEVICE_ID

# shellcheck disable=SC1090
set -a
source "${TARGETS_FILE}"
set +a

if [[ -z "${ADMIN_USERNAME:-}" || -z "${ADMIN_PASSWORD:-}" ]]; then
  echo "FAIL: set ADMIN_USERNAME and ADMIN_PASSWORD in ${TARGETS_FILE}" >&2
  echo "      Copy from ~/hcg-core/.env on the Pi (see docs/run-local.md)" >&2
  exit 1
fi
if [[ "${ADMIN_PASSWORD}" == "change_me" ]]; then
  echo "FAIL: ADMIN_PASSWORD is still the example placeholder in ${TARGETS_FILE}" >&2
  echo "      Use the value from ~/hcg-core/.env on the Pi" >&2
  exit 1
fi

if [[ ! -x "${SENTINEL_ROOT}/.venv/bin/pytest" ]]; then
  python3 -m venv "${SENTINEL_ROOT}/.venv"
  "${SENTINEL_ROOT}/.venv/bin/pip" install -q httpx pytest pytest-timeout PyYAML requests
fi
export PATH="${SENTINEL_ROOT}/.venv/bin:${PATH}"

echo "==> sentinel pr-gate-hub"
"${SENTINEL_ROOT}/bin/sentinel" --local pr-gate-hub
