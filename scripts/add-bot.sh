#!/usr/bin/env bash
# Attach one Discord bot to one OpenClaw agent.
#
#   scripts/add-bot.sh <agent-id> <account-id> <token-file>
#   scripts/add-bot.sh deepseek xu-bot ~/discord-xu.token
#
# The token is read from a file on purpose: it never has to be pasted into a
# terminal transcript, a chat window, or this repo. Delete the file afterwards.
set -euo pipefail

AGENT="${1:?usage: add-bot.sh <agent-id> <account-id> <token-file>}"
ACCOUNT="${2:?usage: add-bot.sh <agent-id> <account-id> <token-file>}"
TOKEN_FILE="${3:?usage: add-bot.sh <agent-id> <account-id> <token-file>}"

[ -f "$TOKEN_FILE" ] || { echo "token file not found: $TOKEN_FILE" >&2; exit 1; }

# OpenClaw needs Node >= 22.22.3, and the shims
# pick `node` off PATH, which is not the same Node everywhere on this machine.
NODE_BIN=""
for candidate in "$(command -v node 2>/dev/null || true)" "$HOME"/node/bin/node "$HOME"/.nvm/versions/node/*/bin/node /opt/homebrew/bin/node /usr/local/bin/node /usr/bin/node; do
  [ -n "$candidate" ] && [ -x "$candidate" ] || continue
  if "$candidate" -e 'const [maj,min,pat]=process.versions.node.split(".").map(Number);process.exit((maj>24||(maj===24&&min>=15)||(maj===22&&(min>22||(min===22&&pat>=3))))?0:1)' 2>/dev/null; then
    NODE_BIN="$candidate"
    break
  fi
done
[ -n "$NODE_BIN" ] || { echo "no Node >= 22.22.3 found" >&2; exit 1; }
PATH="$(dirname "$NODE_BIN"):/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$HOME/.local/bin"
export PATH

OPENCLAW_CMD=(openclaw)
OPENCLAW_BIN="$(command -v openclaw 2>/dev/null || true)"
if [ -n "$OPENCLAW_BIN" ] && [ -f "$OPENCLAW_BIN" ]; then
  OPENCLAW_ENTRY="$(sed -n 's/.*node" "\([^"]*openclaw\/dist\/entry\.js\)".*/\1/p' "$OPENCLAW_BIN" | head -1)"
  if [ -n "$OPENCLAW_ENTRY" ] && [ -f "$OPENCLAW_ENTRY" ]; then
    OPENCLAW_CMD=("$NODE_BIN" "$OPENCLAW_ENTRY")
  fi
fi

chmod 600 "$TOKEN_FILE" 2>/dev/null || true

# --token-file is rejected by the Discord channel ("Discord requires token"),
# so the value has to be passed inline. It is visible in `ps` for the moment the
# command runs; the file still keeps it out of shell history and this repo.
"${OPENCLAW_CMD[@]}" channels add \
  --channel discord \
  --account "$ACCOUNT" \
  --name "$ACCOUNT" \
  --token "$(cat "$TOKEN_FILE")"

"${OPENCLAW_CMD[@]}" agents bind --agent "$AGENT" --bind "discord:$ACCOUNT"

echo
echo "Bound $ACCOUNT -> agent $AGENT. Verify:"
echo "  openclaw agents list --bindings"
echo "  openclaw channels status"
echo "Then delete the token file: rm $TOKEN_FILE"
