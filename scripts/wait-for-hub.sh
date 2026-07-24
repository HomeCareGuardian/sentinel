#!/usr/bin/env bash
set -euo pipefail

: "${HUB_BASE_URL:=http://127.0.0.1:8080}"
HUB="${HUB_BASE_URL}"
HUB_MAX="${1:-${E2E_HUB_READY_TIMEOUT:-300}}"
elapsed=0

# /health is on the LAN-gate setup allowlist, so a direct probe works even on
# hubs past setup mode. When the hub is not directly reachable (off-LAN run),
# fall back to probing loopback over SSH exec — the same path the ssh-exec
# transport uses for the suites.
probe() {
  if curl -sf --max-time 5 "${HUB%/}/health" >/dev/null 2>&1; then
    return 0
  fi
  if [[ -n "${PI_HOST:-}" ]]; then
    ssh -o BatchMode=yes -o ConnectTimeout=5 "${HUB_SSH_USER:-pi}@${PI_HOST}" \
      "curl -sf --max-time 5 http://127.0.0.1:8080/health" >/dev/null 2>&1 && return 0
  fi
  return 1
}

while [[ "${elapsed}" -lt "${HUB_MAX}" ]]; do
  if probe; then
    echo "OK: hub /health (${HUB})"
    exit 0
  fi
  sleep 5
  elapsed=$((elapsed + 5))
  echo "… waiting for hub (${elapsed}s / ${HUB_MAX}s)"
done

echo "FAIL: hub not reachable at ${HUB} (direct or via ssh ${PI_HOST:-<unset>})" >&2
exit 1
