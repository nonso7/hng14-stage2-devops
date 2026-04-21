#!/usr/bin/env bash
#
# Simulates a rolling update for a Compose service:
#   1. Starts a replacement container for $SERVICE alongside the current one,
#      reusing the same image/network/env.
#   2. Waits up to $TIMEOUT seconds for the new container to report
#      healthy (via Docker HEALTHCHECK).
#   3. On success: stops and removes the old container.
#      On failure: removes the new container, leaves the old one running,
#      and exits non-zero.
#
set -euo pipefail

SERVICE="${1:-worker}"
TIMEOUT="${TIMEOUT:-60}"

log() { echo "[rolling-deploy:$SERVICE] $*"; }

old_container="$(docker compose ps -q "$SERVICE")"
if [[ -z "$old_container" ]]; then
  log "ERROR: no running container for service '$SERVICE'"
  exit 1
fi
log "current container: $old_container"

image="$(docker inspect -f '{{.Config.Image}}' "$old_container")"
network="$(docker inspect -f '{{range $k,$v := .NetworkSettings.Networks}}{{$k}}{{end}}' "$old_container")"
new_name="${SERVICE}_rolling_new_$$"

env_file="$(mktemp)"
trap 'rm -f "$env_file"' EXIT
docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$old_container" > "$env_file"

log "starting replacement $new_name from $image on network $network"
docker rm -f "$new_name" >/dev/null 2>&1 || true
docker run -d --name "$new_name" --network "$network" --env-file "$env_file" "$image" >/dev/null

log "waiting up to ${TIMEOUT}s for $new_name to become healthy"
deadline=$(( $(date +%s) + TIMEOUT ))
while : ; do
  if (( $(date +%s) > deadline )); then
    log "TIMEOUT: $new_name did not become healthy within ${TIMEOUT}s — aborting"
    docker rm -f "$new_name" >/dev/null 2>&1 || true
    log "old container $old_container left running"
    exit 1
  fi

  health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$new_name" 2>/dev/null || echo unknown)"
  log "  health=$health"

  case "$health" in
    healthy) break ;;
    unhealthy)
      log "FAIL: $new_name reported unhealthy — aborting"
      docker rm -f "$new_name" >/dev/null 2>&1 || true
      exit 1
      ;;
    *) sleep 2 ;;
  esac
done

log "new container healthy; stopping old container $old_container"
docker stop "$old_container" >/dev/null
docker rm   "$old_container" >/dev/null
log "rolling deploy complete"
