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
chmod +x scripts/*.sh

APP_USER="${MATADOR_PI_EDGE_USER:-matador-edge}"
SYSTEMCTL_BIN="$(command -v systemctl)"
HOSTNAMECTL_BIN="$(command -v hostnamectl)"
TRUE_BIN="$(command -v true)"
case "$TRUE_BIN" in
  /*) ;;
  *) TRUE_BIN="/usr/bin/true" ;;
esac
SUDOERS_FILE="/etc/sudoers.d/matador-pi-edge-agent"
cat > "${SUDOERS_FILE}.tmp" <<EOF
$APP_USER ALL=(root) NOPASSWD: $TRUE_BIN
$APP_USER ALL=(root) NOPASSWD: $SYSTEMCTL_BIN enable --now matador-pi-edge-update.timer
$APP_USER ALL=(root) NOPASSWD: $SYSTEMCTL_BIN disable --now matador-pi-edge-update.timer
$APP_USER ALL=(root) NOPASSWD: $SYSTEMCTL_BIN reboot
$APP_USER ALL=(root) NOPASSWD: $HOSTNAMECTL_BIN set-hostname *
$APP_USER ALL=(root) NOPASSWD: $APP_DIR/scripts/set-hostname.sh *
$APP_USER ALL=(root) NOPASSWD: $APP_DIR/scripts/update.sh
EOF
chmod 0440 "${SUDOERS_FILE}.tmp"
visudo -cf "${SUDOERS_FILE}.tmp"
mv "${SUDOERS_FILE}.tmp" "$SUDOERS_FILE"

cp "deploy/$SERVICE_NAME" "/etc/systemd/system/$SERVICE_NAME"
cp deploy/matador-pi-edge-update.service /etc/systemd/system/matador-pi-edge-update.service
cp deploy/matador-pi-edge-update.timer /etc/systemd/system/matador-pi-edge-update.timer
systemctl daemon-reload
systemctl restart "$SERVICE_NAME"
systemctl status "$SERVICE_NAME" --no-pager -l
