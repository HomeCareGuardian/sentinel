#!/usr/bin/env bash
# Virtual Customer Hub helpers — compose lifecycle for the Sentinel digital twin.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${ROOT}/docker-compose.virtual-hub.yml"
ENV_FILE="${VCH_ENV_FILE:-${ROOT}/config/targets.virtual-hub.env}"
COMPOSE=(docker compose -f "${COMPOSE_FILE}")

if [[ -f "${ENV_FILE}" ]]; then
  COMPOSE+=(--env-file "${ENV_FILE}")
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
fi

HUB_BASE_URL="${HUB_BASE_URL:-http://127.0.0.1:${HUB_PORT:-8080}}"
HA_BASE_URL="${HA_BASE_URL:-http://127.0.0.1:8123}"

usage() {
  cat <<'EOF'
Usage: virtual-hub.sh <command> [args]

Commands:
  up [profiles]     Start postgres + HA + hcg-core (optional: simulator)
  down              Stop and remove containers (keeps volumes)
  status            docker compose ps
  wait-healthy      Wait until hub /health succeeds
  bootstrap-ha      Complete HA onboarding and write HA_TOKEN into env file
  deploy [tag]      Set HCG_IMAGE tag (default: latest), pull, recreate hub
  pull              Pull pinned hub / HA / postgres images
  run-tests         wait-healthy + pytest -m functional
  run-scenario NAME One-shot accelerated scenario via simulator image

Examples:
  ./scripts/virtual-hub.sh up
  ./scripts/virtual-hub.sh up simulator
  ./scripts/virtual-hub.sh deploy sha-abc123
  ./scripts/virtual-hub.sh run-tests
EOF
}

cmd_up() {
  local profiles=()
  if [[ "${1:-}" == "simulator" ]]; then
    profiles+=(--profile simulator)
  fi
  "${COMPOSE[@]}" "${profiles[@]}" up -d postgres homeassistant
  python3 "${ROOT}/virtual_hub/bootstrap_ha.py" \
    --ha-url "${HA_BASE_URL}" \
    --env-file "${ENV_FILE}" \
    --write-token
  # Re-source in case bootstrap wrote HA_TOKEN
  if [[ -f "${ENV_FILE}" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "${ENV_FILE}"
    set +a
  fi
  "${COMPOSE[@]}" "${profiles[@]}" up -d
}

cmd_down() {
  "${COMPOSE[@]}" --profile simulator down
}

cmd_status() {
  "${COMPOSE[@]}" ps
}

cmd_wait_healthy() {
  local timeout="${E2E_HUB_READY_TIMEOUT:-180}"
  local url="${HUB_BASE_URL%/}/health"
  echo "Waiting for ${url} (timeout=${timeout}s)..."
  local start
  start="$(date +%s)"
  while true; do
    if curl -fsS "${url}" >/dev/null 2>&1; then
      echo "Hub healthy."
      return 0
    fi
    if (( "$(date +%s)" - start >= timeout )); then
      echo "FAIL: hub not healthy within ${timeout}s" >&2
      return 1
    fi
    sleep 3
  done
}

cmd_bootstrap_ha() {
  python3 "${ROOT}/virtual_hub/bootstrap_ha.py" \
    --ha-url "${HA_BASE_URL}" \
    --env-file "${ENV_FILE}" \
    --write-token
}

cmd_pull() {
  "${COMPOSE[@]}" pull postgres homeassistant hcg-core || true
  "${COMPOSE[@]}" pull postgres homeassistant hcg-core
}

cmd_deploy() {
  local tag="${1:-latest}"
  local image="${HCG_IMAGE_REPO:-ghcr.io/homecareguardian/hcg-core}:${tag}"
  mkdir -p "$(dirname "${ENV_FILE}")"
  if [[ ! -f "${ENV_FILE}" ]]; then
    cp "${ROOT}/config/targets.virtual-hub.env.example" "${ENV_FILE}"
  fi
  if grep -q '^HCG_IMAGE=' "${ENV_FILE}" 2>/dev/null; then
    # portable in-place edit
    local tmp
    tmp="$(mktemp)"
    sed "s|^HCG_IMAGE=.*|HCG_IMAGE=${image}|" "${ENV_FILE}" >"${tmp}"
    mv "${tmp}" "${ENV_FILE}"
  else
    echo "HCG_IMAGE=${image}" >>"${ENV_FILE}"
  fi
  echo "Deploying ${image}"
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
  cmd_pull
  "${COMPOSE[@]}" up -d hcg-core
  cmd_wait_healthy
}

cmd_run_tests() {
  cmd_wait_healthy
  export HUB_BASE_URL
  export ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
  export ADMIN_PASSWORD="${ADMIN_PASSWORD:-vch_admin_change_me}"
  cd "${ROOT}"
  if [[ $# -eq 0 ]]; then
    python3 -m pytest -m functional
  else
    python3 -m pytest "$@"
  fi
}

cmd_run_scenario() {
  local name="${1:?scenario name required}"
  "${COMPOSE[@]}" --profile simulator run --rm \
    -e SCENARIO="${name}" \
    -e ACCELERATED=1 \
    -e LOOP_DAYS=0 \
    -e HA_TOKEN="${HA_TOKEN:-}" \
    --entrypoint python \
    day-simulator \
    day_runner.py --once --scenario "${name}" --accelerated
}

main() {
  local cmd="${1:-help}"
  shift || true
  case "${cmd}" in
    up) cmd_up "$@" ;;
    down) cmd_down "$@" ;;
    status) cmd_status ;;
    wait-healthy) cmd_wait_healthy ;;
    bootstrap-ha) cmd_bootstrap_ha ;;
    pull) cmd_pull ;;
    deploy) cmd_deploy "$@" ;;
    run-tests) cmd_run_tests "$@" ;;
    run-scenario) cmd_run_scenario "$@" ;;
    help|-h|--help) usage ;;
    *)
      echo "Unknown command: ${cmd}" >&2
      usage >&2
      exit 1
      ;;
  esac
}

main "$@"
