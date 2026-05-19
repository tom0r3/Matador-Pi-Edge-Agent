#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${MATADOR_PI_EDGE_APP_DIR:-/opt/matador-pi-edge-agent}"
APP_USER="${MATADOR_PI_EDGE_USER:-matador-edge}"
REPO_URL="${MATADOR_PI_EDGE_REPO_URL:-https://github.com/tom0r3/Matador-Pi-Edge-Agent.git}"
SERVICE_NAME="matador-pi-edge-agent.service"

if [ "$(id -u)" -ne 0 ]; then
  echo "Please run as root, for example: sudo ./scripts/install.sh" >&2
  exit 1
fi

echo "Installing Matador Pi Edge Agent..."

apt-get update
apt-get install -y ca-certificates curl git python3 python3-venv sqlite3

if ! id "$APP_USER" >/dev/null 2>&1; then
  useradd --system --home-dir /var/lib/matador-pi-edge-agent --shell /usr/sbin/nologin "$APP_USER"
fi

if [ -d "$APP_DIR/.git" ]; then
  git -C "$APP_DIR" pull --ff-only
else
  rm -rf "$APP_DIR"
  git clone "$REPO_URL" "$APP_DIR"
fi

cd "$APP_DIR"

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

cp "deploy/$SERVICE_NAME" "/etc/systemd/system/$SERVICE_NAME"
systemctl daemon-reload
systemctl enable --now "$SERVICE_NAME"

echo
echo "Matador Pi Edge Agent installed."
echo "Watch the setup/claim logs with:"
echo "  sudo journalctl -u $SERVICE_NAME -f"
echo
echo "Approve the Pi in Matador Admin > Pending Pi Edge Agents."

