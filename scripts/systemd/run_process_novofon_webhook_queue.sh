#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/home/bogdan/buyesai}"
PYTHON_BIN="${PYTHON_BIN:-$PROJECT_DIR/env/bin/python}"
INTERVAL_SEC="${NOVOFON_WEBHOOK_QUEUE_INTERVAL_SEC:-5}"
LIMIT="${NOVOFON_WEBHOOK_QUEUE_LIMIT:-50}"
MAX_RETRIES="${NOVOFON_WEBHOOK_QUEUE_MAX_RETRIES:-5}"
RETRY_FAILED="${NOVOFON_WEBHOOK_QUEUE_RETRY_FAILED:-1}"
FAILED_BACKOFF_BASE_SEC="${NOVOFON_WEBHOOK_QUEUE_FAILED_BACKOFF_BASE_SEC:-30}"
FAILED_BACKOFF_MAX_SEC="${NOVOFON_WEBHOOK_QUEUE_FAILED_BACKOFF_MAX_SEC:-900}"
RECLAIM_STALE_PROCESSING_AFTER_SEC="${NOVOFON_WEBHOOK_QUEUE_RECLAIM_STALE_PROCESSING_AFTER_SEC:-300}"

cd "$PROJECT_DIR"

while true; do
  if [[ "$RETRY_FAILED" == "1" ]]; then
    "$PYTHON_BIN" manage.py process_novofon_webhook_queue --limit "$LIMIT" --max-retries "$MAX_RETRIES" --retry-failed --failed-backoff-base-sec "$FAILED_BACKOFF_BASE_SEC" --failed-backoff-max-sec "$FAILED_BACKOFF_MAX_SEC" --reclaim-stale-processing-after-sec "$RECLAIM_STALE_PROCESSING_AFTER_SEC"
  else
    "$PYTHON_BIN" manage.py process_novofon_webhook_queue --limit "$LIMIT" --max-retries "$MAX_RETRIES" --failed-backoff-base-sec "$FAILED_BACKOFF_BASE_SEC" --failed-backoff-max-sec "$FAILED_BACKOFF_MAX_SEC" --reclaim-stale-processing-after-sec "$RECLAIM_STALE_PROCESSING_AFTER_SEC"
  fi
  sleep "$INTERVAL_SEC"
done
