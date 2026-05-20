#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${MATADOR_PI_EDGE_APP_DIR:-/opt/matador-pi-edge-agent}"
SERVICE_NAME="matador-pi-edge-agent.service"
SHUTDOWN_AFTER_PREP="${MATADOR_PI_EDGE_SHUTDOWN_AFTER_PREP:-1}"

if [ "$(id -u)" -ne 0 ]; then
  echo "Please run as root, for example: sudo ./scripts/prepare-golden-image.sh" >&2
  exit 1
fi

if [ ! -x "$APP_DIR/scripts/install.sh" ]; then
  echo "Matador Pi Edge Agent installer not found at $APP_DIR/scripts/install.sh" >&2
  exit 1
fi

echo "Preparing Matador Pi Edge Agent golden image..."
systemctl stop "$SERVICE_NAME" >/dev/null 2>&1 || true
systemctl disable "$SERVICE_NAME" >/dev/null 2>&1 || true

cd "$APP_DIR"
git reset --hard
git pull --ff-only

MATADOR_PI_EDGE_START_NOW=0 MATADOR_PI_EDGE_HOSTNAME=matador-pi-edge ./scripts/install.sh

echo
echo "Golden image preparation complete. Do not reboot before cloning."
echo
"$APP_DIR/scripts/status.sh" || true
echo
echo "Current hostname: $(hostname)"

if [ "$SHUTDOWN_AFTER_PREP" = "1" ] || [ "$SHUTDOWN_AFTER_PREP" = "true" ] || [ "$SHUTDOWN_AFTER_PREP" = "yes" ]; then
  echo
  echo "Shutting down now. Remove and clone the SD card after power-off."
  shutdown now
else
  echo
  echo "Shutdown skipped. When ready to clone, run: sudo shutdown now"
fi
