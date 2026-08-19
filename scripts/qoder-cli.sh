#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
. "$ROOT/scripts/env.sh"
load_env_file "$ROOT/.env"

if [ -z "${QODER_PERSONAL_ACCESS_TOKEN:-}" ] && [ -f "$HOME/.openclaw/secrets.env" ]; then
  load_env_file "$HOME/.openclaw/secrets.env"
fi

# Resolve qoder rather than hardcoding one machine's nvm path. The gateway runs
# under launchd/systemd with a minimal PATH, so PATH alone is not enough — fall
# back to the nvm and system locations the same way add-bot.sh finds node.
QODER_BIN="${QODER_BIN:-$(command -v qoder || true)}"
if [ -z "$QODER_BIN" ]; then
  for candidate in "$HOME"/node/bin/qoder "$HOME"/.nvm/versions/node/*/bin/qoder /opt/homebrew/bin/qoder /usr/local/bin/qoder /usr/bin/qoder; do
    [ -x "$candidate" ] && QODER_BIN="$candidate" && break
  done
fi
[ -n "$QODER_BIN" ] || { echo "qoder not found; set QODER_BIN or add it to PATH" >&2; exit 1; }

exec "$QODER_BIN" "$@"
