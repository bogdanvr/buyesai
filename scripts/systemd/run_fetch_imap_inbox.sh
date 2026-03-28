#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/home/bogdan/buyesai}"
PYTHON_BIN="${PYTHON_BIN:-$PROJECT_DIR/env/bin/python}"
INTERVAL_SEC="${FETCH_IMAP_INBOX_INTERVAL_SEC:-60}"
LIMIT="${FETCH_IMAP_INBOX_LIMIT:-50}"
SEARCH_CRITERIA="${FETCH_IMAP_INBOX_SEARCH:-ALL}"
MAILBOX="${FETCH_IMAP_INBOX_MAILBOX:-}"

cd "$PROJECT_DIR"

while true; do
  if [[ -n "$MAILBOX" ]]; then
    "$PYTHON_BIN" manage.py fetch_imap_inbox --limit "$LIMIT" --search "$SEARCH_CRITERIA" --mailbox "$MAILBOX"
  else
    "$PYTHON_BIN" manage.py fetch_imap_inbox --limit "$LIMIT" --search "$SEARCH_CRITERIA"
  fi
  sleep "$INTERVAL_SEC"
done
