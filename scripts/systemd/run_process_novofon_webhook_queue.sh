#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/home/bogdan/buyesai}"
PYTHON_BIN="${PYTHON_BIN:-$PROJECT_DIR/env/bin/python}"
INTERVAL_SEC="${NOVOFON_WEBHOOK_QUEUE_INTERVAL_SEC:-5}"
IDLE_INTERVAL_SEC="${NOVOFON_WEBHOOK_QUEUE_IDLE_INTERVAL_SEC:-15}"
ERROR_INTERVAL_SEC="${NOVOFON_WEBHOOK_QUEUE_ERROR_INTERVAL_SEC:-15}"
LIMIT="${NOVOFON_WEBHOOK_QUEUE_LIMIT:-50}"
MAX_RETRIES="${NOVOFON_WEBHOOK_QUEUE_MAX_RETRIES:-5}"
RETRY_FAILED="${NOVOFON_WEBHOOK_QUEUE_RETRY_FAILED:-1}"
FAILED_BACKOFF_BASE_SEC="${NOVOFON_WEBHOOK_QUEUE_FAILED_BACKOFF_BASE_SEC:-30}"
FAILED_BACKOFF_MAX_SEC="${NOVOFON_WEBHOOK_QUEUE_FAILED_BACKOFF_MAX_SEC:-900}"
RECLAIM_STALE_PROCESSING_AFTER_SEC="${NOVOFON_WEBHOOK_QUEUE_RECLAIM_STALE_PROCESSING_AFTER_SEC:-300}"
COMMAND_TIMEOUT_SEC="${NOVOFON_WEBHOOK_QUEUE_COMMAND_TIMEOUT_SEC:-120}"

cd "$PROJECT_DIR"

while true; do
  OUTPUT=""
  if [[ "$RETRY_FAILED" == "1" ]]; then
    if OUTPUT=$(timeout --signal=TERM --kill-after=15s "${COMMAND_TIMEOUT_SEC}s" \
      "$PYTHON_BIN" manage.py process_novofon_webhook_queue --limit "$LIMIT" --max-retries "$MAX_RETRIES" --retry-failed --failed-backoff-base-sec "$FAILED_BACKOFF_BASE_SEC" --failed-backoff-max-sec "$FAILED_BACKOFF_MAX_SEC" --reclaim-stale-processing-after-sec "$RECLAIM_STALE_PROCESSING_AFTER_SEC" 2>&1); then
      printf '%s\n' "$OUTPUT"
      if grep -Eq "'processed': [1-9][0-9]*" <<<"$OUTPUT"; then
        sleep "$INTERVAL_SEC"
      else
        sleep "$IDLE_INTERVAL_SEC"
      fi
      continue
    fi
  else
    if OUTPUT=$(timeout --signal=TERM --kill-after=15s "${COMMAND_TIMEOUT_SEC}s" \
      "$PYTHON_BIN" manage.py process_novofon_webhook_queue --limit "$LIMIT" --max-retries "$MAX_RETRIES" --failed-backoff-base-sec "$FAILED_BACKOFF_BASE_SEC" --failed-backoff-max-sec "$FAILED_BACKOFF_MAX_SEC" --reclaim-stale-processing-after-sec "$RECLAIM_STALE_PROCESSING_AFTER_SEC" 2>&1); then
      printf '%s\n' "$OUTPUT"
      if grep -Eq "'processed': [1-9][0-9]*" <<<"$OUTPUT"; then
        sleep "$INTERVAL_SEC"
      else
        sleep "$IDLE_INTERVAL_SEC"
      fi
      continue
    fi
  fi
  printf '%s\n' "$OUTPUT" >&2
  sleep "$ERROR_INTERVAL_SEC"
done
