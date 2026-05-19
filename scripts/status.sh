#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${MATADOR_PI_EDGE_APP_DIR:-/opt/matador-pi-edge-agent}"
STATE_DIR="${MATADOR_PI_EDGE_STATE_DIR:-/var/lib/matador-pi-edge-agent}"
SERVICE_NAME="matador-pi-edge-agent.service"

echo "Matador Pi Edge Agent status"
echo "============================"
systemctl --no-pager --full status "$SERVICE_NAME" || true
echo

if [ -f "$APP_DIR/VERSION" ]; then
  echo "Code version: $(tr -d '\r\n' < "$APP_DIR/VERSION")"
fi

"$APP_DIR/.venv/bin/python" - <<'PY'
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

state_dir = Path(os.environ.get("MATADOR_PI_EDGE_STATE_DIR", "/var/lib/matador-pi-edge-agent"))
state_path = state_dir / "state.json"
spool_path = state_dir / "outbound-spool.sqlite3"

state = {}
if state_path.exists():
    state = json.loads(state_path.read_text(encoding="utf-8"))

print(f"Claim code: {state.get('claim_code') or '-'}")
print(f"Device token present: {'yes' if state.get('device_token') else 'no'}")
print(f"Processor enabled: {state.get('processor_enabled', True)}")
print(f"Streaming enabled: {state.get('streaming_enabled', True)}")
print(f"Last config: {state.get('last_config_at') or '-'}")
print(f"Last processor host: {state.get('last_processor_host') or '-'}")
print(f"Locked processor: {state.get('locked_processor_identity') or '-'}")
print(f"Discovered processors: {len(state.get('last_discovered_processors') or [])}")
for processor in state.get("last_discovered_processors") or []:
    title = " - ".join(str(processor.get(key) or "") for key in ("name", "model", "serial_number") if processor.get(key))
    print(f"  - {title or 'GoFree processor'} @ {processor.get('last_host') or '-'}:{processor.get('port') or 2053}")
print(f"Counters: {state.get('counters') or {}}")

if spool_path.exists():
    with sqlite3.connect(spool_path) as conn:
        row = conn.execute("SELECT count(*), min(created_at), max(created_at) FROM outbound_payloads").fetchone()
    print(f"Message queue pending: {row[0] or 0}")
else:
    print("Message queue pending: spool database not created yet")
PY
