#!/usr/bin/env python3
"""Print the curated open-loops brief for Xu.

The file is intentionally separate from raw inboxes or private stores. It is a
small, human-curated status board that Xu can read without being handed Gmail,
Slack, or a full second brain.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path


KNOWLEDGE_DIR = Path(os.path.expanduser("~/data/knowledge"))
OPEN_LOOPS_FILE = KNOWLEDGE_DIR / "open-loops.md"


TEMPLATE = """# Open Loops

## Project name

- Status: one-line current state
- Next: the next concrete action
- Owner: who should move it
- Channel: Discord channel/thread to continue in
- Updated: YYYY-MM-DD
- Notes: optional constraints or blockers
"""


def parse_sections(markdown: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    current_title: str | None = None
    current_lines: list[str] = []

    for line in markdown.splitlines():
        match = re.match(r"^##\s+(.+?)\s*$", line)
        if match:
            if current_title:
                body = "\n".join(current_lines).strip()
                sections.append((current_title, body))
            current_title = match.group(1).strip()
            current_lines = []
            continue
        if current_title:
            current_lines.append(line)

    if current_title:
        body = "\n".join(current_lines).strip()
        sections.append((current_title, body))
    return sections


def compact_section(title: str, body: str) -> str:
    fields: dict[str, str] = {}
    extras: list[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        match = re.match(r"^-\s*([A-Za-z][A-Za-z -]*):\s*(.*)$", stripped)
        if match:
            fields[match.group(1).strip().lower()] = match.group(2).strip()
        else:
            extras.append(stripped)

    bits = [f"## {title}"]
    for key in ["status", "next", "owner", "channel", "updated", "notes"]:
        value = fields.get(key)
        if value:
            bits.append(f"- {key.title()}: {value}")
    for extra in extras[:3]:
        bits.append(extra)
    return "\n".join(bits)


def main() -> int:
    parser = argparse.ArgumentParser(description="Print curated open project loops.")
    parser.add_argument("--raw", action="store_true", help="Print the markdown file as-is.")
    parser.add_argument("--template", action="store_true", help="Print the expected file template.")
    args = parser.parse_args()

    if args.template:
        print(TEMPLATE.rstrip())
        return 0

    if not OPEN_LOOPS_FILE.exists():
        print("Open loops file is missing.")
        print(f"Create: {OPEN_LOOPS_FILE}")
        print()
        print(TEMPLATE.rstrip())
        return 1

    markdown = OPEN_LOOPS_FILE.read_text(encoding="utf-8").strip()
    if args.raw:
        print(markdown)
        return 0

    sections = parse_sections(markdown)
    if not sections:
        print(markdown)
        return 0

    print("=== PRIVATE CURATED OPEN LOOPS ===")
    print("Use as current working state. Do not quote private details unless needed.")
    print()
    for index, (title, body) in enumerate(sections, start=1):
        if index > 1:
            print()
        print(compact_section(title, body))
    print()
    print("=== END OPEN LOOPS ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
