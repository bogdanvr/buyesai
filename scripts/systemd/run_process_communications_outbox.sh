#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/home/bogdan/buyesai}"
PYTHON_BIN="${PYTHON_BIN:-$PROJECT_DIR/env/bin/python}"
INTERVAL_SEC="${PROCESS_COMMUNICATIONS_OUTBOX_INTERVAL_SEC:-5}"
IDLE_INTERVAL_SEC="${PROCESS_COMMUNICATIONS_OUTBOX_IDLE_INTERVAL_SEC:-15}"
ERROR_INTERVAL_SEC="${PROCESS_COMMUNICATIONS_OUTBOX_ERROR_INTERVAL_SEC:-15}"
LIMIT="${PROCESS_COMMUNICATIONS_OUTBOX_LIMIT:-100}"
COMMAND_TIMEOUT_SEC="${PROCESS_COMMUNICATIONS_OUTBOX_COMMAND_TIMEOUT_SEC:-120}"

cd "$PROJECT_DIR"

while true; do
  OUTPUT=""
  if OUTPUT=$(timeout --signal=TERM --kill-after=15s "${COMMAND_TIMEOUT_SEC}s" \
    "$PYTHON_BIN" manage.py process_communications_outbox --limit "$LIMIT" 2>&1); then
    printf '%s\n' "$OUTPUT"
    if grep -Eq "processed=[1-9][0-9]*" <<<"$OUTPUT"; then
      sleep "$INTERVAL_SEC"
    else
      sleep "$IDLE_INTERVAL_SEC"
    fi
    continue
  fi
  printf '%s\n' "$OUTPUT" >&2
  sleep "$ERROR_INTERVAL_SEC"
done
