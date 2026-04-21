#!/usr/bin/env bash
set -euo pipefail

FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
TIMEOUT="${TIMEOUT:-60}"

log() { echo "[integration] $*"; }

log "Submitting a job to $FRONTEND_URL/submit"
submit_response="$(curl -fsS -X POST "$FRONTEND_URL/submit")"
log "  response: $submit_response"

job_id="$(printf '%s' "$submit_response" | python3 -c 'import json,sys; print(json.load(sys.stdin)["job_id"])')"
if [[ -z "$job_id" ]]; then
  log "FAIL: submit did not return a job_id"
  exit 1
fi
log "job_id=$job_id"

deadline=$(( $(date +%s) + TIMEOUT ))
while : ; do
  now=$(date +%s)
  if (( now > deadline )); then
    log "FAIL: job $job_id did not complete within ${TIMEOUT}s"
    exit 1
  fi

  status_body="$(curl -fsS "$FRONTEND_URL/status/$job_id")"
  status="$(printf '%s' "$status_body" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("status",""))')"
  log "  status=$status"

  case "$status" in
    completed)
      log "PASS: job $job_id completed"
      exit 0
      ;;
    failed)
      log "FAIL: worker reported job $job_id failed"
      exit 1
      ;;
    *)
      sleep 2
      ;;
  esac
done
