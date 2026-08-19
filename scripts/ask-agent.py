#!/usr/bin/env python3
"""Ask another OpenClaw agent a question or delegate a sub-task.

    scripts/ask-agent <agent_name> "<prompt>"

Supported agent names/aliases:
- qoder / tho / thợ       -> Qoder CLI (Code analysis, security, diffs)
- gemini / chua / chùa    -> Google Gemini (Long document reading, quick search)
- codex / vethang / vé tháng -> Codex CLI (Complex reasoning, architectural plans)
- deepseek / xu           -> DeepSeek API (Quick summary, pricing)
- claude                  -> Claude (Internal reviewer)
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

AGENT_ALIASES = {
    "qoder": "qoder",
    "tho": "qoder",
    "thợ": "qoder",
    "thoi": "qoder",
    "gemini": "gemini",
    "chua": "gemini",
    "chùa": "gemini",
    "codex": "codex",
    "vethang": "codex",
    "ve-thang": "codex",
    "vé tháng": "codex",
    "deepseek": "deepseek",
    "xu": "deepseek",
    "claude": "claude",
}

TIMEOUT_SECONDS = 90


def resolve_agent(name: str) -> str:
    cleaned = name.strip().lower()
    if cleaned in AGENT_ALIASES:
        return AGENT_ALIASES[cleaned]
    return cleaned


def find_node_and_openclaw() -> list[str]:
    # Look for openclaw CLI or entrypoint
    openclaw_bin = subprocess.run(["command", "-v", "openclaw"], capture_output=True, text=True, shell=True).stdout.strip()
    if openclaw_bin:
        return ["openclaw"]
    
    # Fallback to local / nvm node execution
    candidates = [
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
