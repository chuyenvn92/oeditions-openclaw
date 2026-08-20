#!/usr/bin/env python3
"""Summarize OpenClaw token/cost usage from local session logs.

Read-only. It scans ~/.openclaw/agents/*/sessions and reports recent assistant
usage grouped by Discord session/channel.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


OPENCLAW_HOME = Path(os.path.expanduser("~/.openclaw"))


@dataclass
class Usage:
    key: str
    agent: str
    channel: str = ""
    session_id: str = ""
    last_interaction_ms: int = 0
    assistant_turns: int = 0
    tool_calls: int = 0
    tool_failures: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read: int = 0
    cache_write: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    last_text: str = ""
    models: set[str] = field(default_factory=set)


def as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def as_float(value: Any) -> float:
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def text_from_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for item in content:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "text":
            parts.append(item.get("text", ""))
        elif item.get("type") == "toolCall":
            parts.append(f"[tool:{item.get('name', 'unknown')}]")
    return " ".join(parts).strip()


def collect_agent(agent_dir: Path, days: float, discord_only: bool) -> list[Usage]:
    sessions_dir = agent_dir / "sessions"
    sessions_index = sessions_dir / "sessions.json"
    data = load_json(sessions_index)
    if not isinstance(data, dict):
        return []

    cutoff_ms = int((time.time() - days * 86400) * 1000) if days > 0 else 0
    rows: list[Usage] = []
    for key, entry in data.items():
        if not isinstance(entry, dict):
            continue
        if discord_only and "discord:" not in key and entry.get("channel") != "discord":
            continue
        last_ms = as_int(entry.get("lastInteractionAt") or entry.get("updatedAt"))
        if cutoff_ms and last_ms and last_ms < cutoff_ms:
            continue

        session_id = entry.get("sessionId")
        if not session_id:
            continue
        log_path = sessions_dir / f"{session_id}.jsonl"
        if not log_path.exists():
            continue

        row = Usage(
            key=key,
            agent=agent_dir.name,
            channel=entry.get("groupChannel") or entry.get("displayName") or entry.get("lastTo") or "",
            session_id=session_id,
            last_interaction_ms=last_ms,
        )
        for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                record = json.loads(line)
            except Exception:
                continue
            message = record.get("message", {})
            if not isinstance(message, dict):
                continue
            role = message.get("role")
            if role == "assistant":
                usage = message.get("usage")
                if isinstance(usage, dict):
                    row.assistant_turns += 1
                    row.input_tokens += as_int(usage.get("input"))
                    row.output_tokens += as_int(usage.get("output"))
                    row.cache_read += as_int(usage.get("cacheRead"))
                    row.cache_write += as_int(usage.get("cacheWrite"))
                    row.total_tokens += as_int(usage.get("totalTokens") or usage.get("total"))
                    cost = usage.get("cost")
                    if isinstance(cost, dict):
                        row.cost_usd += as_float(cost.get("total"))
                    row.models.add(str(message.get("model") or ""))
                    text = text_from_content(message.get("content"))
                    if text:
                        row.last_text = text
            elif role == "toolResult":
                if message.get("isError"):
                    row.tool_failures += 1

            content = message.get("content")
            if isinstance(content, list):
                row.tool_calls += sum(1 for item in content if isinstance(item, dict) and item.get("type") == "toolCall")

        if row.assistant_turns or row.tool_calls:
            rows.append(row)
    return rows


def format_money(value: float) -> str:
    if value < 0.0001:
        return f"${value:.6f}"
    if value < 0.01:
        return f"${value:.5f}"
    return f"${value:.4f}"


def risk_label(row: Usage) -> str:
    avg_tokens = row.total_tokens / max(row.assistant_turns, 1)
    if row.tool_failures:
        return "check-tools"
    if row.assistant_turns >= 12 or avg_tokens >= 30000:
        return "consider-reset"
    if avg_tokens >= 18000:
        return "watch"
    return "ok"


def main() -> int:
    parser = argparse.ArgumentParser(description="Report OpenClaw token usage from session logs.")
    parser.add_argument("--days", type=float, default=1.0, help="Look back this many days; 0 means all time.")
    parser.add_argument("--agent", help="Agent id to inspect, e.g. deepseek.")
    parser.add_argument("--all", action="store_true", help="Include non-Discord sessions.")
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args()

    agents_root = OPENCLAW_HOME / "agents"
    if args.agent:
        agent_dirs = [agents_root / args.agent]
    else:
        agent_dirs = [p for p in agents_root.iterdir() if p.is_dir()] if agents_root.exists() else []

    rows: list[Usage] = []
    for agent_dir in agent_dirs:
        rows.extend(collect_agent(agent_dir, args.days, discord_only=not args.all))

    rows.sort(key=lambda row: row.last_interaction_ms, reverse=True)
    rows = rows[: max(args.limit, 1)]

    if args.json:
        print(json.dumps([
            {
                "agent": r.agent,
                "channel": r.channel,
                "key": r.key,
                "assistant_turns": r.assistant_turns,
                "tool_calls": r.tool_calls,
                "tool_failures": r.tool_failures,
                "input_tokens": r.input_tokens,
                "output_tokens": r.output_tokens,
                "cache_read": r.cache_read,
                "cache_write": r.cache_write,
                "total_tokens": r.total_tokens,
                "cost_usd": r.cost_usd,
                "risk": risk_label(r),
                "last_text": r.last_text[:300],
            }
            for r in rows
        ], ensure_ascii=False, indent=2))
        return 0

    print(f"Token report — last {args.days:g} day(s), {'all sessions' if args.all else 'Discord sessions only'}")
    print()
    if not rows:
        print("No matching usage found.")
        return 0

    for r in rows:
        avg = int(r.total_tokens / max(r.assistant_turns, 1))
        print(f"## {r.agent} {r.channel or r.key}")
        print(f"- Turns: {r.assistant_turns} assistant / {r.tool_calls} tool calls / {r.tool_failures} failures")
        print(f"- Tokens: total {r.total_tokens}, avg/turn {avg}, input {r.input_tokens}, output {r.output_tokens}, cacheRead {r.cache_read}")
        print(f"- Cost: {format_money(r.cost_usd)}")
        print(f"- Risk: {risk_label(r)}")
        if r.last_text:
            print(f"- Last: {r.last_text[:180]}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
