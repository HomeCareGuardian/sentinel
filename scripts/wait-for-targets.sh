#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SENTINEL_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
# shellcheck source=/dev/null
source "${SENTINEL_ROOT}/lib/common.sh"
load_config

HUB_MAX="${E2E_HUB_READY_TIMEOUT:-300}"
WEB_MAX="${E2E_WEBSITE_READY_TIMEOUT:-120}"

wait_url() {
  local url="$1"
  local label="$2"
  local max="$3"
  local elapsed=0
  while [[ "${elapsed}" -lt "${max}" ]]; do
    if curl -sf -o /dev/null "${url}" 2>/dev/null; then
      echo "OK: ${label} (${url})"
      return 0
    fi
    sleep 5
    elapsed=$((elapsed + 5))
    echo "… waiting for ${label} (${elapsed}s / ${max}s)"
  done
  echo "FAIL: ${label} not reachable: ${url}" >&2
  return 1
}

wait_url "${HUB_BASE_URL}/health" "hub /health" "${HUB_MAX}"
wait_url "${WEBSITE_BASE_URL}/" "website" "${WEB_MAX}"
