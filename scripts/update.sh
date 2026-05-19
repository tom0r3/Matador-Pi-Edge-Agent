#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${MATADOR_PI_EDGE_APP_DIR:-/opt/matador-pi-edge-agent}"
SERVICE_NAME="matador-pi-edge-agent.service"

if [ "$(id -u)" -ne 0 ]; then
  echo "Please run as root, for example: sudo ./scripts/update.sh" >&2
  exit 1
fi

if [ ! -d "$APP_DIR/.git" ]; then
  echo "Matador Pi Edge Agent repo not found at $APP_DIR" >&2
  echo "Run the installer first." >&2
  exit 1
fi

echo "Updating Matador Pi Edge Agent..."

cd "$APP_DIR"
git pull --ff-only

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

cp "deploy/$SERVICE_NAME" "/etc/systemd/system/$SERVICE_NAME"
systemctl daemon-reload
systemctl restart "$SERVICE_NAME"
systemctl status "$SERVICE_NAME" --no-pager -l

