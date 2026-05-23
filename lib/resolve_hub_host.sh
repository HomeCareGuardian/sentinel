# Resolve HUB_HOST → PI_HOST + HUB_BASE_URL (no fleet registry required).
#
# Usage (from bash):
#   HUB_HOST=hcg-hub-5fcf7e73cfe7a329 source lib/resolve_hub_host.sh
#   hub_host_apply
#
# Rules:
#   - Bare device id (no dot) → append .local for mDNS
#   - Already has a dot (FQDN or IP) → use as-is
#   - HUB_BASE_URL in env wins unless HUB_HOST is set (HUB_HOST overrides URL host)

hub_host_normalize() {
  local raw="${1:-}"
  raw="${raw#http://}"
  raw="${raw#https://}"
  raw="${raw%%/*}"
  # host:port in HUB_HOST
  raw="${raw%%:*}"

  if [[ -z "${raw}" ]]; then
    echo "hub_host_normalize: empty host" >&2
    return 1
  fi

  if [[ "${raw}" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    printf '%s' "${raw}"
    return 0
  fi

  if [[ "${raw}" != *.* ]]; then
    printf '%s.local' "${raw}"
    return 0
  fi

  printf '%s' "${raw}"
}

hub_host_apply() {
  if [[ -z "${HUB_HOST:-}" ]]; then
    return 0
  fi

  local fqdn
  fqdn="$(hub_host_normalize "${HUB_HOST}")" || return 1

  : "${HUB_PORT:=8080}"
  export PI_HOST="${fqdn}"
  export HUB_DEVICE_ID="${HUB_DEVICE_ID:-${HUB_HOST%%.*}}"
  export HUB_BASE_URL="http://${fqdn}:${HUB_PORT}"
}
