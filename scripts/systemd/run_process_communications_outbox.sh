#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/home/bogdan/buyesai}"
PYTHON_BIN="${PYTHON_BIN:-$PROJECT_DIR/env/bin/python}"
INTERVAL_SEC="${PROCESS_COMMUNICATIONS_OUTBOX_INTERVAL_SEC:-5}"
LIMIT="${PROCESS_COMMUNICATIONS_OUTBOX_LIMIT:-100}"

cd "$PROJECT_DIR"

while true; do
  "$PYTHON_BIN" manage.py process_communications_outbox --limit "$LIMIT"
  sleep "$INTERVAL_SEC"
done
