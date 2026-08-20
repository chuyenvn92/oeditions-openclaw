#!/usr/bin/env python3
"""Update one project block in the curated open-loops board.

This is intentionally not a generic file editor. It only touches
~/data/knowledge/open-loops.md and only writes the known fields used by
scripts/open-loops.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import subprocess
import sys
from pathlib import Path


KNOWLEDGE_DIR = Path(os.path.expanduser("~/data/knowledge"))
OPEN_LOOPS_FILE = KNOWLEDGE_DIR / "open-loops.md"
FIELDS = ["Status", "Next", "Owner", "Channel", "Updated", "Notes"]


def normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", title.strip()).casefold()


def parse_blocks(markdown: str) -> tuple[str, list[tuple[str, list[str]]]]:
    lines = markdown.splitlines()
    prelude: list[str] = []
    blocks: list[tuple[str, list[str]]] = []
    current_title: str | None = None
    current_lines: list[str] = []

    for line in lines:
        match = re.match(r"^##\s+(.+?)\s*$", line)
        if match:
            if current_title is None:
                prelude = current_lines
            else:
                blocks.append((current_title, current_lines))
            current_title = match.group(1).strip()
            current_lines = []
            continue
        current_lines.append(line)

    if current_title is None:
        prelude = lines
    else:
        blocks.append((current_title, current_lines))

    return "\n".join(prelude).rstrip(), blocks


def fields_from_lines(lines: list[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in lines:
        match = re.match(r"^-\s*([A-Za-z][A-Za-z -]*):\s*(.*)$", line.strip())
        if not match:
            continue
        raw_key, value = match.group(1).strip(), match.group(2).strip()
        for field in FIELDS:
            if raw_key.casefold() == field.casefold():
                fields[field] = value
                break
    return fields


def render_block(title: str, fields: dict[str, str]) -> str:
    lines = [f"## {title}", ""]
    for field in FIELDS:
        value = fields.get(field, "").strip()
        if value:
            lines.append(f"- {field}: {value}")
    return "\n".join(lines).rstrip()


def reindex_if_possible() -> None:
    index_script = Path(__file__).with_name("kb-index.py")
    if not index_script.exists():
        return
    subprocess.run([sys.executable, str(index_script)], check=False, timeout=45)


def main() -> int:
    parser = argparse.ArgumentParser(description="Update one open-loop project block.")
    parser.add_argument("project", help="Project section title to update or create.")
    parser.add_argument("--status")
    parser.add_argument("--next")
    parser.add_argument("--owner")
    parser.add_argument("--channel")
    parser.add_argument("--updated")
    parser.add_argument("--notes")
    parser.add_argument("--no-index", action="store_true", help="Skip KB re-index after writing.")
    args = parser.parse_args()

    updates = {
        "Status": args.status,
        "Next": args.next,
        "Owner": args.owner,
        "Channel": args.channel,
        "Updated": args.updated,
        "Notes": args.notes,
    }
    updates = {key: value.strip() for key, value in updates.items() if value and value.strip()}
    if not updates:
        print("Error: provide at least one field to update.", file=sys.stderr)
        return 2
    if "Updated" not in updates:
        updates["Updated"] = dt.date.today().isoformat()

    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    if OPEN_LOOPS_FILE.exists():
        markdown = OPEN_LOOPS_FILE.read_text(encoding="utf-8")
    else:
        markdown = "# Open Loops\n\nPrivate current-state board for Xu and Vé Tháng.\n"

    prelude, blocks = parse_blocks(markdown)
    target = normalize_title(args.project)
    changed = False
    rendered_blocks: list[str] = []

    for title, lines in blocks:
        if normalize_title(title) == target:
            fields = fields_from_lines(lines)
            fields.update(updates)
            rendered_blocks.append(render_block(title, fields))
            changed = True
        else:
            rendered_blocks.append(render_block(title, fields_from_lines(lines)))

    if not changed:
        rendered_blocks.append(render_block(args.project.strip(), updates))

    output = prelude or "# Open Loops"
    output = output.rstrip() + "\n\n" + "\n\n".join(rendered_blocks).rstrip() + "\n"
    tmp_path = OPEN_LOOPS_FILE.with_suffix(".md.tmp")
    tmp_path.write_text(output, encoding="utf-8")
    os.replace(tmp_path, OPEN_LOOPS_FILE)

    if not args.no_index:
        reindex_if_possible()

    action = "Updated" if changed else "Created"
    print(f"{action} open loop: {args.project.strip()}")
    for field in FIELDS:
        if field in updates:
            print(f"- {field}: {updates[field]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
