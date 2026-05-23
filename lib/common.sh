# Shared helpers for Sentinel — black-box only (no product repo paths).

export E2E_TARGET="${E2E_TARGET:-local}"

load_config() {
  SENTINEL_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

  local profile="${E2E_TARGET:-local}"
  local profile_file=""

  if [[ -f "${SENTINEL_ROOT}/config/targets.${profile}.env" ]]; then
    profile_file="${SENTINEL_ROOT}/config/targets.${profile}.env"
  elif [[ -f "${SENTINEL_ROOT}/config/targets.${profile}.env.example" ]]; then
    profile_file="${SENTINEL_ROOT}/config/targets.${profile}.env.example"
  else
    echo "FAIL: no config for profile '${profile}' (expected config/targets.${profile}.env)" >&2
    exit 1
  fi

  # shellcheck disable=SC1090
  set -a
  source "${profile_file}"
  set +a

  if [[ -f "${SENTINEL_ROOT}/config/targets.env" ]]; then
    # shellcheck disable=SC1091
    source "${SENTINEL_ROOT}/config/targets.env"
  fi

  : "${HUB_BASE_URL:=http://127.0.0.1:8080}"
  : "${WEBSITE_BASE_URL:=http://127.0.0.1:3000}"
  : "${E2E_TARGET:=${profile}}"
  : "${E2E_TARGET_LABEL:=${profile}}"

  if [[ -n "${HUB_HOST:-}" ]]; then
    # shellcheck source=/dev/null
    source "${SENTINEL_ROOT}/lib/resolve_hub_host.sh"
    hub_host_apply
  fi

  export SENTINEL_ROOT HUB_BASE_URL WEBSITE_BASE_URL E2E_TARGET E2E_TARGET_LABEL
  [[ -n "${HUB_HOST:-}" ]] && export HUB_HOST
  [[ -n "${PI_HOST:-}" ]] && export PI_HOST
  [[ -n "${HUB_DEVICE_ID:-}" ]] && export HUB_DEVICE_ID
  export E2E_REPORTS_DIR="${SENTINEL_ROOT}/reports/${E2E_TARGET}"
}

e2e_print_target() {
  load_config
  echo "Sentinel target: ${E2E_TARGET_LABEL} (profile=${E2E_TARGET})"
  [[ -n "${HUB_HOST:-}" ]] && echo "  HUB_HOST=${HUB_HOST}"
  echo "  HUB_BASE_URL=${HUB_BASE_URL}"
  echo "  WEBSITE_BASE_URL=${WEBSITE_BASE_URL}"
  echo "  reports=${E2E_REPORTS_DIR}"
}

e2e_check_targets() {
  load_config
  "${SENTINEL_ROOT}/scripts/wait-for-targets.sh"
}

e2e_check_hub_only() {
  load_config
  export HUB_BASE_URL E2E_HUB_READY_TIMEOUT
  "${SENTINEL_ROOT}/scripts/wait-for-hub.sh"
}

e2e_bootstrap() {
  load_config
  python3 "${SENTINEL_ROOT}/scripts/bootstrap_hub.py"
  "${SENTINEL_ROOT}/scripts/verify-bootstrap.sh"
}

e2e_journeys() {
  local tier="p0"
  for arg in "$@"; do
    case "${arg}" in
      --p0) tier="p0" ;;
      --p1) tier="p1" ;;
    esac
  done
  load_config
  mkdir -p "${E2E_REPORTS_DIR}"

  local marker="sentinel_e2e"
  if [[ "${tier}" == "p0" ]]; then
    marker="sentinel_e2e and (j1 or j2 or j3 or j4 or api_catalog)"
  fi

  cd "${SENTINEL_ROOT}"
  if [[ -x "${SENTINEL_ROOT}/.venv/bin/pytest" ]]; then
    export PATH="${SENTINEL_ROOT}/.venv/bin:${PATH}"
  fi

  HUB_BASE_URL="${HUB_BASE_URL}" \
  pytest suites/core -m "${marker}" \
    --junitxml="${E2E_REPORTS_DIR}/core-junit.xml" \
    -v
}

e2e_contract() {
  load_config
  cd "${SENTINEL_ROOT}"
  python3 contracts/check_live_openapi.py
}

e2e_website() {
  local mode="p0"
  for arg in "$@"; do
    [[ "${arg}" == "--full" ]] && mode="full"
  done
  load_config
  mkdir -p "${E2E_REPORTS_DIR}"
  cd "${SENTINEL_ROOT}/suites/website"
  npm ci --prefer-offline 2>/dev/null || npm install
  npx playwright install chromium 2>/dev/null || true
  if [[ "${mode}" == "p0" ]]; then
    WEBSITE_BASE_URL="${WEBSITE_BASE_URL}" npx playwright test --grep @p0
  else
    WEBSITE_BASE_URL="${WEBSITE_BASE_URL}" npx playwright test
  fi
}

e2e_ios() {
  load_config
  export HUB_BASE_URL
  cd "${SENTINEL_ROOT}"
  python3 suites/ios/run_hub_e2e.py
}

e2e_pr_gate_hub() {
  load_config
  mkdir -p "${E2E_REPORTS_DIR}"
  e2e_print_target
  echo "Scope: hub only (J1–J4)"

  e2e_check_hub_only
  e2e_contract
  e2e_bootstrap
  e2e_journeys --p0
  e2e_ios

  E2E_REPORTS_DIR="${E2E_REPORTS_DIR}" python3 "${SENTINEL_ROOT}/scripts/merge_junit.py" 2>/dev/null || true
  E2E_REPORTS_DIR="${E2E_REPORTS_DIR}" python3 "${SENTINEL_ROOT}/scripts/failure_summary.py" 2>/dev/null || true
  echo "==> pr-gate-hub complete (${E2E_TARGET})"
}

e2e_pr_gate() {
  load_config
  mkdir -p "${E2E_REPORTS_DIR}"
  e2e_print_target

  e2e_check_targets
  e2e_contract
  e2e_bootstrap
  e2e_journeys --p0
  e2e_website
  e2e_ios

  E2E_REPORTS_DIR="${E2E_REPORTS_DIR}" python3 "${SENTINEL_ROOT}/scripts/merge_junit.py" 2>/dev/null || true
  E2E_REPORTS_DIR="${E2E_REPORTS_DIR}" python3 "${SENTINEL_ROOT}/scripts/failure_summary.py" 2>/dev/null || true
  echo "==> pr-gate complete (${E2E_TARGET})"
}

e2e_all() {
  e2e_pr_gate
  e2e_website --full
}
