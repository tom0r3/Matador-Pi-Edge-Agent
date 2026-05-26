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

NODE_BIN="$(find_tool "${MATADOR_DEV_NODE:-}" \
  node \
  "${windows_home}/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe" \
)" || {
  printf 'Node.js not found. Set MATADOR_DEV_NODE or install Node.js.\n' >&2
  exit 1
}

step() {
  printf '\n==> %s\n' "$1"
}

step "Python compile"
"$PYTHON_BIN" -m py_compile \
  edge_agent/pi_edge_agent.py \
  gofree_collector/dashboard.py \
  gofree_collector/edge_ingest.py

step "Embedded browser JavaScript parse"
"$NODE_BIN" - <<'NODE'
const fs = require("fs");
const files = ["web/nextindex.html", "web/pi_edge_diagnostics.html", "web/admin.html", "web/diagnostics.html", "web/sql.html"];
for (const file of files) {
  const html = fs.readFileSync(file, "utf8");
  const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((match) => match[1]);
  for (const source of scripts) new Function(source);
  console.log(`${file}: ${scripts.length} script block(s) ok`);
}
NODE

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
  git diff --check -- \
    edge_agent/pi_edge_agent.py \
    gofree_collector/dashboard.py \
    gofree_collector/edge_ingest.py \
    web/nextindex.html \
    web/pi_edge_diagnostics.html \
    web/admin.html \
    web/diagnostics.html \
    web/sql.html \
    README.md \
    CHANGELOG.md \
    docs/edge_agent.md \
    docs/pi_edge_agent.md \
    docs/sql_admin.md \
    scripts/update.sh \
    scripts/install.sh \
    scripts/status.sh \
    scripts/dev-check.ps1 \
    scripts/dev-check.sh
else
  printf 'git not found; skipping diff whitespace check.\n'
fi

printf '\nDevelopment checks passed.\n'
