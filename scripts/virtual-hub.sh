#!/usr/bin/env bash
# Virtual Customer Hub helpers — compose lifecycle for the Sentinel digital twin.
# Uses the `docker` CLI (works with Docker Engine or Podman docker-compat).
# Override with VCH_COMPOSE if needed.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${ROOT}/docker-compose.virtual-hub.yml"
ENV_FILE="${VCH_ENV_FILE:-${ROOT}/config/targets.virtual-hub.env}"

# Podman's `docker compose` delegates to podman-compose (often pip --user).
export PATH="${HOME}/Library/Python/3.14/bin:${HOME}/Library/Python/3.13/bin:${HOME}/.local/bin:${PATH}"

# Do not override DOCKER_CONFIG with an empty auth file — that drops
# `docker login ghcr.io` / Podman credentials and breaks private pulls.
# Public images use fully-qualified refs (docker.io/..., ghcr.io/...) so the
# broken gcloud docker-credential helper is not required.

resolve_compose() {
  local -a cmd=()
  if [[ -n "${VCH_COMPOSE:-}" ]]; then
    # shellcheck disable=SC2206
    cmd=(${VCH_COMPOSE})
  elif command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    cmd=(docker compose)
  else
    echo "FAIL: need 'docker compose' (Docker Engine or Podman docker-compat)" >&2
    echo "  On Podman: pip install --user podman-compose  (must be on PATH)" >&2
    echo "  Checked PATH for: ${HOME}/Library/Python/*/bin and ~/.local/bin" >&2
    docker compose version >&2 || true
    exit 1
  fi
  COMPOSE=("${cmd[@]}" -f "${COMPOSE_FILE}")
  if [[ -f "${ENV_FILE}" ]]; then
    COMPOSE+=(--env-file "${ENV_FILE}")
  fi
  echo "Using compose: ${COMPOSE[*]}"
}

resolve_compose

if [[ -f "${ENV_FILE}" ]]; then
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

Uses \`docker compose\` (Docker Engine or Podman docker-compat).
Set VCH_COMPOSE to override.

Commands:
  up [simulator]    Start postgres + HA + hcg-core (optional: day-simulator)
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
  local with_sim=0
  if [[ "${1:-}" == "simulator" ]]; then
    with_sim=1
  fi
  # Start HA side first so bootstrap can obtain HA_TOKEN before hub comes up.
  "${COMPOSE[@]}" up -d postgres homeassistant
  if [[ ! -f "${ENV_FILE}" ]]; then
    cp "${ROOT}/config/targets.virtual-hub.env.example" "${ENV_FILE}"
  fi
  python3 "${ROOT}/virtual_hub/bootstrap_ha.py" \
    --ha-url "${HA_BASE_URL}" \
    --env-file "${ENV_FILE}" \
    --write-token
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
  # Re-resolve so --env-file picks up HA_TOKEN for hcg-core.
  resolve_compose
  local hub_image="${HCG_IMAGE:-ghcr.io/homecareguardian/hcg-core:latest}"
  if ! docker image inspect "${hub_image}" >/dev/null 2>&1; then
    echo "Pulling hub image ${hub_image}..."
    if ! docker pull "${hub_image}"; then
      echo "FAIL: cannot pull hub image (GHCR package read required)." >&2
      echo "  docker login ghcr.io -u <user>" >&2
      echo "  Ask an org admin to grant read on package hcg-core, then retry." >&2
      echo "Postgres + Home Assistant are up; HA_TOKEN is written. Hub not started." >&2
      return 1
    fi
  fi
  if [[ "${with_sim}" -eq 1 ]]; then
    "${COMPOSE[@]}" up -d postgres homeassistant hcg-core day-simulator
  else
    "${COMPOSE[@]}" up -d postgres homeassistant hcg-core
  fi
}

cmd_down() {
  "${COMPOSE[@]}" down
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
      "${COMPOSE[@]}" ps >&2 || true
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
  resolve_compose
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
  if [[ -f "${ENV_FILE}" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "${ENV_FILE}"
    set +a
  fi
  "${COMPOSE[@]}" run --rm \
    -e SCENARIO="${name}" \
    -e ACCELERATED=1 \
    -e LOOP_DAYS=0 \
    -e HA_TOKEN="${HA_TOKEN:-}" \
    -e HA_BASE_URL=http://homeassistant:8123 \
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
