#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${MATADOR_PI_EDGE_APP_DIR:-/opt/matador-pi-edge-agent}"
STATE_DIR="${MATADOR_PI_EDGE_STATE_DIR:-/var/lib/matador-pi-edge-agent}"
APP_USER="${MATADOR_PI_EDGE_USER:-matador-edge}"
REPO_URL="${MATADOR_PI_EDGE_REPO_URL:-https://github.com/tom0r3/Matador-Pi-Edge-Agent.git}"
SERVICE_NAME="matador-pi-edge-agent.service"
START_NOW="${MATADOR_PI_EDGE_START_NOW:-1}"
TARGET_HOSTNAME="${MATADOR_PI_EDGE_HOSTNAME:-matador-pi-edge}"

if [ "$(id -u)" -ne 0 ]; then
  echo "Please run as root, for example: sudo ./scripts/install.sh" >&2
  exit 1
fi

echo "Installing Matador Pi Edge Agent..."

apt-get update
apt-get install -y ca-certificates curl git python3 python3-venv sqlite3 sudo

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
chmod +x scripts/*.sh

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
if [ "$START_NOW" = "0" ] || [ "$START_NOW" = "false" ] || [ "$START_NOW" = "no" ]; then
  rm -rf "$STATE_DIR"
  install -d -o "$APP_USER" -g "$APP_USER" -m 0750 "$STATE_DIR"
  touch "$STATE_DIR/golden-image-hostname.pending"
  chown "$APP_USER:$APP_USER" "$STATE_DIR/golden-image-hostname.pending"
  "$APP_DIR/scripts/set-hostname.sh" "$TARGET_HOSTNAME"
  systemctl enable "$SERVICE_NAME"
  systemctl stop "$SERVICE_NAME" >/dev/null 2>&1 || true
  START_MESSAGE="Service is enabled for the customer's first boot, but was not started during install."
else
  systemctl enable --now "$SERVICE_NAME"
  START_MESSAGE="Service has been started and will phone home when network is available."
fi

echo
echo "Matador Pi Edge Agent installed."
echo "$START_MESSAGE"
echo "Watch the setup/claim logs with:"
echo "  sudo journalctl -u $SERVICE_NAME -f"
echo
echo "Check local status with:"
echo "  sudo $APP_DIR/scripts/status.sh"
echo
echo "Optional daily updates can be enabled with:"
echo "  sudo systemctl enable --now matador-pi-edge-update.timer"
echo
echo "Approve the Pi in Matador Admin > Pending Pi Edge Agents."
