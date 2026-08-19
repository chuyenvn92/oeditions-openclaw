#!/usr/bin/env bash
# Copy persona files from this repo into the live OpenClaw agent workspaces.
#
#   scripts/apply-personas.sh
#
# Idempotent: IDENTITY.md is overwritten, the shared room rules are appended to
# AGENTS.md only once (guarded by a marker line).
set -euo pipefail

DIR="$(cd "$(dirname "$0")/.." && pwd)"
WORKSPACES="$HOME/.openclaw/workspaces"
MARKER="## Room rules (shared Discord channel)"
ROOM_BEGIN="<!-- Appended to each bot agent's AGENTS.md by scripts/apply-personas.sh."
ROSTER_MARKER="## Who else is in the room"
ROSTER_FILE="$DIR/personas/ROSTER.md"
[ -f "$DIR/personas/ROSTER.local.md" ] && ROSTER_FILE="$DIR/personas/ROSTER.local.md"

# In-place edit that works on both seds. BSD (macOS) requires an argument to
# -i and GNU (Linux) refuses one, so `sed -i ''` deletes blocks here and dies on
# a server. Writing to a temp file and moving it needs neither dialect.
#   $1 = sed script, $2 = file
sed_inplace() {
  sed "$1" "$2" > "$2.tmp" && mv "$2.tmp" "$2"
}

for persona in "$DIR"/personas/*/; do
  agent="$(basename "$persona")"
  ws="$WORKSPACES/$agent"

  if [ ! -d "$ws" ]; then
    echo "skip $agent: no workspace at $ws"
    continue
  fi

  cp "$persona/IDENTITY.md" "$ws/IDENTITY.md"

  # SOUL.md carries behaviour, including the rule that an agent answering
  # another agent must never emit ANNOUNCE_SKIP — that reply is what the channel
  # shows, so skipping it leaves the person waiting in silence.
  [ -f "$persona/SOUL.md" ] && cp "$persona/SOUL.md" "$ws/SOUL.md"

  # Clear any CODING block left by an older version of this script.
  [ -f "$ws/AGENTS.md" ] && sed_inplace '/<!-- CODING:BEGIN/,/CODING:END -->/d' "$ws/AGENTS.md"

  # Room rules change too (routing, cost policy), so drop the old block before
  # re-appending rather than skipping when the heading is already there. Trim
  # from the leading HTML comment when present; older versions trimmed from the
  # heading and left duplicate comments behind.
  python3 - "$ws/AGENTS.md" "$ROOM_BEGIN" <<'DEDUP_ROOM_COMMENTS'
import sys
p, room_begin = sys.argv[1], sys.argv[2]
lines = open(p).read().split("\n")
out = []
i = 0
while i < len(lines):
    if (
        lines[i].startswith(room_begin)
        and i + 2 < len(lines)
        and "Keep it short:" in lines[i + 1]
        and "measured baseline" in lines[i + 2]
    ):
        i += 3
        if i < len(lines) and lines[i].strip() == "":
            i += 1
        continue
    out.append(lines[i])
    i += 1
open(p, "w").write("\n".join(out).rstrip() + "\n")
DEDUP_ROOM_COMMENTS

  if grep -qF "$MARKER" "$ws/AGENTS.md" 2>/dev/null; then
    python3 - "$ws/AGENTS.md" "$MARKER" "$ROOM_BEGIN" <<'TRIM'
import sys
p, marker, room_begin = sys.argv[1], sys.argv[2], sys.argv[3]
lines = open(p).read().split("\n")
for i, l in enumerate(lines):
    if l.strip() == marker.strip():
        start = i
        for j in range(i - 1, -1, -1):
            if lines[j].startswith(room_begin):
                start = j
            elif start != i and lines[j].strip() == "":
                start = j
            elif start != i:
                break
        open(p, "w").write("\n".join(lines[:start]).rstrip() + "\n")
        break
TRIM
  fi

  printf '\n' >> "$ws/AGENTS.md"
  cat "$DIR/personas/ROOM-RULES.md" >> "$ws/AGENTS.md"
  echo "$agent: identity updated, room rules appended"

  # Replace the roster block (bounded by its BEGIN/END markers, so anything
  # appended after it — the coding block — survives).
  sed_inplace '/<!-- ROSTER:BEGIN -->/,/<!-- ROSTER:END -->/d' "$ws/AGENTS.md"
  printf '\n' >> "$ws/AGENTS.md"
  cat "$ROSTER_FILE" >> "$ws/AGENTS.md"
  echo "$agent: roster refreshed"

  # IDENTITY.md again, this time inside AGENTS.md. OpenClaw reads the file and
  # `agents list` prints the name back, but a CLI-backed agent never receives it:
  # asked for its own emoji, codex answered with a colleague's and then deduced
  # its billing model from the roster, and qoder said outright it did not know
  # which bot it was. AGENTS.md does arrive, so the identity goes here too.
  # Harmless duplication for API-backed agents, and the only copy CLI ones see.
  sed_inplace '/<!-- IDENTITY:BEGIN -->/,/<!-- IDENTITY:END -->/d' "$ws/AGENTS.md"
  {
    printf '\n<!-- IDENTITY:BEGIN -->\n\n## You, specifically\n\n'
    sed '1{/^# IDENTITY/d;}' "$persona/IDENTITY.md"
    printf '\n<!-- IDENTITY:END -->\n'
  } >> "$ws/AGENTS.md"
  echo "$agent: identity inlined into AGENTS.md"
done
