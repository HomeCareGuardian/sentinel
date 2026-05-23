#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SENTINEL_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
# shellcheck source=/dev/null
source "${SENTINEL_ROOT}/lib/common.sh"
load_config

python3 "${SCRIPT_DIR}/verify_bootstrap.py" \
  --hub-url "${HUB_BASE_URL}" \
  --manifest "${SENTINEL_ROOT}/journeys/bootstrap-manifest.yaml"
