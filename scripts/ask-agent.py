#!/usr/bin/env python3
"""Ask Vé Tháng / Codex a question or delegate a bounded sub-task.

    scripts/ask-agent <agent_name> "<prompt>"

The live allowlist intentionally permits only Codex / Vé Tháng. Thợ must be
tagged directly by the human.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

AGENT_ALIASES = {
    "codex": "codex",
    "vethang": "codex",
    "ve-thang": "codex",
    "vé tháng": "codex",
}

TIMEOUT_SECONDS = 90
ALLOWED_AGENT_IDS = {"codex"}


def resolve_agent(name: str) -> str:
    cleaned = name.strip().lower()
    if cleaned in AGENT_ALIASES:
        return AGENT_ALIASES[cleaned]
    return cleaned


def find_node_and_openclaw() -> list[str]:
    # Look for openclaw CLI or entrypoint
    openclaw_bin = shutil.which("openclaw")
    if openclaw_bin:
        return [openclaw_bin]
    
    # Fallback to local / nvm node execution
    candidates = [
        os.path.expanduser("~/node/bin/openclaw"),
        os.path.expanduser("~/.nvm/versions/node/v22.22.3/bin/openclaw"),
        "/opt/homebrew/bin/openclaw",
        "/usr/local/bin/openclaw",
    ]
    for c in candidates:
        if os.path.exists(c) and os.access(c, os.X_OK):
            return [c]
    return ["openclaw"]


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: ask-agent <agent_name> \"<prompt>\"", file=sys.stderr)
        return 2

    raw_agent = sys.argv[1]
    prompt = " ".join(sys.argv[2:]).strip()

    if not prompt:
        print("Error: Empty prompt.", file=sys.stderr)
        return 2

    agent_id = resolve_agent(raw_agent)
    if agent_id not in ALLOWED_AGENT_IDS:
        print(
            "Error: ask-agent is only allowlisted for codex / Vé Tháng. "
            "Ask the human to tag Thợ directly.",
            file=sys.stderr,
        )
        return 2

    openclaw_cmd = find_node_and_openclaw()

    cmd = openclaw_cmd + [
        "agent",
        "--agent", agent_id,
        "--message", prompt,
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()

        if proc.returncode != 0:
            print(f"Error calling agent '{agent_id}' (exit code {proc.returncode}):", file=sys.stderr)
            if stderr:
                print(stderr, file=sys.stderr)
            if stdout:
                print(stdout)
            return proc.returncode

        print(f"=== AGENT RESPONSE (Agent: {agent_id}) ===")
        print(stdout if stdout else "(No response text received)")
        print(f"=== END AGENT RESPONSE ===")
        return 0

    except subprocess.TimeoutExpired:
        print(f"Error: Agent '{agent_id}' timed out after {TIMEOUT_SECONDS}s.", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error executing ask-agent: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
