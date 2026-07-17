#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

find_tool() {
  local env_value="$1"
  shift
  if [ -n "$env_value" ]; then
    printf '%s\n' "$env_value"
    return 0
  fi
  for candidate in "$@"; do
    if [ -n "$candidate" ] && command -v "$candidate" >/dev/null 2>&1; then
      command -v "$candidate"
      return 0
    fi
    if [ -n "$candidate" ] && [ -x "$candidate" ]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

windows_home=""
if [ -n "${USERPROFILE:-}" ] && command -v cygpath >/dev/null 2>&1; then
  windows_home="$(cygpath -u "$USERPROFILE")"
fi

PYTHON_BIN="$(find_tool "${MATADOR_DEV_PYTHON:-}" \
  python3 \
  python \
  "${windows_home}/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe" \
)" || {
  printf 'Python not found. Set MATADOR_DEV_PYTHON or install Python.\n' >&2
  exit 1
}

step() {
  printf '\n==> %s\n' "$1"
}

step "Python compile"
"$PYTHON_BIN" -m py_compile \
  edge_agent/pi_edge_agent.py \
  edge_agent/navico_advertiser.py

step "Python tests"
"$PYTHON_BIN" -m unittest discover -s tests

step "Browser JavaScript parse"
printf 'No browser JavaScript in the standalone Pi Agent repository.\n'

step "Shell script syntax"
for file in \
  scripts/update.sh \
  scripts/install.sh \
  scripts/status.sh \
  scripts/factory-reset.sh \
  scripts/prepare-golden-image.sh \
  scripts/set-hostname.sh \
  scripts/dev-check.sh
do
  [ -f "$file" ] || continue
  bash -n "$file"
  printf '%s ok\n' "$file"
done

if command -v git >/dev/null 2>&1; then
  step "Git whitespace check"
  git -c "safe.directory=$ROOT_DIR" -C "$ROOT_DIR" diff --check -- \
    edge_agent/pi_edge_agent.py \
    edge_agent/navico_advertiser.py \
    tests/test_navico_advertiser.py \
    README.md \
    CHANGELOG.md \
    VERSION \
    scripts/update.sh \
    scripts/install.sh \
    scripts/status.sh \
    deploy/matador-pi-edge-agent.service \
    scripts/dev-check.ps1 \
    scripts/dev-check.sh
else
  printf 'git not found; skipping diff whitespace check.\n'
fi

printf '\nDevelopment checks passed.\n'
