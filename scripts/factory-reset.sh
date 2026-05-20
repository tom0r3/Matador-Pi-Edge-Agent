#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${MATADOR_PI_EDGE_APP_DIR:-/opt/matador-pi-edge-agent}"
SERVICE_NAME="matador-pi-edge-agent.service"
REBOOT_AFTER_RESET="${MATADOR_PI_EDGE_REBOOT_AFTER_RESET:-1}"

if [ "$(id -u)" -ne 0 ]; then
  echo "Please run as root, for example: sudo ./scripts/factory-reset.sh" >&2
  exit 1
fi

if [ ! -x "$APP_DIR/scripts/install.sh" ]; then
  echo "Matador Pi Edge Agent installer not found at $APP_DIR/scripts/install.sh" >&2
  exit 1
fi

echo "Factory resetting Matador Pi Edge Agent..."
systemctl stop "$SERVICE_NAME" >/dev/null 2>&1 || true
systemctl disable "$SERVICE_NAME" >/dev/null 2>&1 || true

cd "$APP_DIR"
git reset --hard
git pull --ff-only

MATADOR_PI_EDGE_START_NOW=0 MATADOR_PI_EDGE_HOSTNAME=matador-pi-edge ./scripts/install.sh

echo
echo "Factory reset complete. The agent will generate a fresh hostname and claim on next boot."
echo
"$APP_DIR/scripts/status.sh" || true

if [ "$REBOOT_AFTER_RESET" = "1" ] || [ "$REBOOT_AFTER_RESET" = "true" ] || [ "$REBOOT_AFTER_RESET" = "yes" ]; then
  echo
  echo "Rebooting now..."
  systemctl reboot
else
  echo
  echo "Reboot skipped. Start first-boot claim with: sudo reboot"
fi
