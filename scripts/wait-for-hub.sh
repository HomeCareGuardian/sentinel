#!/usr/bin/env bash
set -euo pipefail

: "${HUB_BASE_URL:=http://127.0.0.1:8080}"
HUB="${HUB_BASE_URL}"
HUB_MAX="${1:-${E2E_HUB_READY_TIMEOUT:-300}}"
elapsed=0

while [[ "${elapsed}" -lt "${HUB_MAX}" ]]; do
  if curl -sf "${HUB%/}/health" >/dev/null 2>&1; then
    echo "OK: hub /health (${HUB})"
    exit 0
  fi
  sleep 5
  elapsed=$((elapsed + 5))
  echo "… waiting for hub (${elapsed}s / ${HUB_MAX}s)"
done

echo "FAIL: hub not reachable at ${HUB}" >&2
exit 1
