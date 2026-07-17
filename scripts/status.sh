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
import urllib.request
from pathlib import Path

state_dir = Path(os.environ.get("MATADOR_PI_EDGE_STATE_DIR", "/var/lib/matador-pi-edge-agent"))
state_path = state_dir / "state.json"
spool_path = state_dir / "outbound-spool.sqlite3"
golden_hostname_marker = state_dir / "golden-image-hostname.pending"
update_log_path = state_dir / "update.log"

state = {}
if state_path.exists():
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except PermissionError:
        print(f"State file: permission denied reading {state_path}; run this status script with sudo for full details.")
    except json.JSONDecodeError as exc:
        print(f"State file: invalid JSON in {state_path}: {exc}")

print(f"Claim code: {state.get('claim_code') or '-'}")
print(f"Device token present: {'yes' if state.get('device_token') else 'no'}")
print(f"Golden hostname pending: {'yes' if golden_hostname_marker.exists() else 'no'}")
print(f"Hostname uniqued at: {state.get('hostname_uniqued_at') or '-'}")
print(f"Hostname uniqued from: {state.get('hostname_uniqued_from') or '-'}")
print(f"Requested hostname: {state.get('requested_hostname') or '-'}")
print(f"Hostname uniquing error: {state.get('hostname_uniquing_error') or '-'}")
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
if update_log_path.exists():
    print(f"Update log: {update_log_path}")
    try:
        tail = update_log_path.read_text(encoding="utf-8", errors="replace")[-1200:]
        print("Update log tail:")
        print(tail.rstrip() or "-")
    except PermissionError:
        print("Update log tail: permission denied; run with sudo for full details.")

if spool_path.exists():
    try:
        with sqlite3.connect(spool_path, timeout=30.0) as conn:
            conn.execute("PRAGMA busy_timeout=30000")
            row = conn.execute("SELECT count(*), min(created_at), max(created_at), coalesce(sum(length(payload_json)), 0) FROM outbound_payloads").fetchone()
        print(f"Message queue pending: {row[0] or 0}")
        print(f"Message queue bytes: {row[3] or 0}")
    except PermissionError:
        print(f"Message queue pending: permission denied reading {spool_path}; run with sudo for queue details.")
    except sqlite3.OperationalError as exc:
        print(f"Message queue pending: unable to read spool database: {exc}")
else:
    print("Message queue pending: spool database not created yet")

local_status_port = int(os.environ.get("MATADOR_PI_EDGE_LOCAL_STATUS_PORT", "8080") or "0")
if local_status_port > 0:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{local_status_port}/api/status", timeout=2) as response:
            live_status = json.loads(response.read().decode("utf-8"))
        navico = ((live_status.get("health") or {}).get("navico_html5_advertiser") or {})
        if navico:
            print(f"Navico advertiser enabled: {navico.get('enabled')}")
            print(f"Navico advertiser running: {navico.get('running')}")
            print(f"Navico MFD interface: {navico.get('interface') or '-'}")
            print(f"Navico MFD address: {navico.get('selected_address') or '-'}")
            print(f"Navico last send: {navico.get('last_send_at') or '-'}")
            print(f"Navico send/errors: {navico.get('send_count') or 0}/{navico.get('error_count') or 0}")
            print(f"Navico last error: {navico.get('last_error') or '-'}")
    except Exception as exc:
        print(f"Navico advertiser live status: unavailable from local status page ({exc})")
PY
