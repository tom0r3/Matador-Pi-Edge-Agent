#!/usr/bin/env bash
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "Please run as root, for example: sudo ./scripts/set-hostname.sh matador-pi-edge-abc123" >&2
  exit 1
fi

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 HOSTNAME" >&2
  exit 1
fi

TARGET_HOSTNAME="$(printf "%s" "$1" | tr '[:upper:]' '[:lower:]')"

if ! printf "%s" "$TARGET_HOSTNAME" | grep -Eq '^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$'; then
  echo "Hostname must contain only lowercase letters, numbers, or hyphens and be 1-63 characters." >&2
  exit 1
fi

hostnamectl set-hostname "$TARGET_HOSTNAME"

HOSTS_FILE="/etc/hosts"
TMP_FILE="$(mktemp /etc/hosts.matador.XXXXXX)"
trap 'rm -f "$TMP_FILE"' EXIT

if [ -f "$HOSTS_FILE" ]; then
  awk -v host="$TARGET_HOSTNAME" '
    BEGIN { done = 0 }
    /^127[.]0[.]1[.]1[[:space:]]/ {
      if (!done) {
        print "127.0.1.1\t" host
        done = 1
      }
      next
    }
    { print }
    END {
      if (!done) {
        print "127.0.1.1\t" host
      }
    }
  ' "$HOSTS_FILE" > "$TMP_FILE"
  chmod --reference="$HOSTS_FILE" "$TMP_FILE" 2>/dev/null || chmod 0644 "$TMP_FILE"
  chown --reference="$HOSTS_FILE" "$TMP_FILE" 2>/dev/null || chown root:root "$TMP_FILE"
else
  printf "127.0.0.1\tlocalhost\n127.0.1.1\t%s\n" "$TARGET_HOSTNAME" > "$TMP_FILE"
  chmod 0644 "$TMP_FILE"
  chown root:root "$TMP_FILE"
fi

mv "$TMP_FILE" "$HOSTS_FILE"
trap - EXIT
