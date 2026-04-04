#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/home/bogdan/buyesai}"
PYTHON_BIN="${PYTHON_BIN:-$PROJECT_DIR/env/bin/python}"
INTERVAL_SEC="${FETCH_IMAP_INBOX_INTERVAL_SEC:-60}"
IDLE_INTERVAL_SEC="${FETCH_IMAP_INBOX_IDLE_INTERVAL_SEC:-180}"
ERROR_INTERVAL_SEC="${FETCH_IMAP_INBOX_ERROR_INTERVAL_SEC:-180}"
LIMIT="${FETCH_IMAP_INBOX_LIMIT:-50}"
SEARCH_CRITERIA="${FETCH_IMAP_INBOX_SEARCH:-ALL}"
MAILBOX="${FETCH_IMAP_INBOX_MAILBOX:-}"
COMMAND_TIMEOUT_SEC="${FETCH_IMAP_INBOX_COMMAND_TIMEOUT_SEC:-180}"

cd "$PROJECT_DIR"

while true; do
  OUTPUT=""
  if [[ -n "$MAILBOX" ]]; then
    if OUTPUT=$(timeout --signal=TERM --kill-after=15s "${COMMAND_TIMEOUT_SEC}s" \
      "$PYTHON_BIN" manage.py fetch_imap_inbox --limit "$LIMIT" --search "$SEARCH_CRITERIA" --mailbox "$MAILBOX" 2>&1); then
      printf '%s\n' "$OUTPUT"
      if grep -Eq "Processed=[1-9][0-9]*" <<<"$OUTPUT"; then
        sleep "$INTERVAL_SEC"
      else
        sleep "$IDLE_INTERVAL_SEC"
      fi
      continue
    fi
  else
    if OUTPUT=$(timeout --signal=TERM --kill-after=15s "${COMMAND_TIMEOUT_SEC}s" \
      "$PYTHON_BIN" manage.py fetch_imap_inbox --limit "$LIMIT" --search "$SEARCH_CRITERIA" 2>&1); then
      printf '%s\n' "$OUTPUT"
      if grep -Eq "Processed=[1-9][0-9]*" <<<"$OUTPUT"; then
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
