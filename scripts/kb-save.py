#!/usr/bin/env python3
"""Save a note or decision to the local knowledge base and re-index.

    scripts/kb-save "<note content>" [--topic <topic_name>]

Examples:
    scripts/kb-save "Quyết định: Dự án OpenClaw chuyển sang dùng PostgreSQL từ tháng 9."
    scripts/kb-save "Sở thích ăn uống: Thích đồ ăn nhạt, ít đường, không ăn hành tây." --topic preferences
"""
from __future__ import annotations

import datetime
import os
import re
import subprocess
import sys

KNOWLEDGE_DIR = os.path.expanduser("~/data/knowledge")


def sanitize_topic(topic: str) -> str:
    topic = topic.strip().lower()
    if topic.endswith(".md"):
        topic = topic[:-3]
    # Keep only safe characters: a-z, 0-9, dash, underscore
    clean = re.sub(r"[^a-z0-9_-]", "-", topic).strip("-")
    if not clean:
        clean = "notes"
    return f"{clean}.md"


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: kb-save \"<note text>\" [--topic <topic_name>]", file=sys.stderr)
        return 2

    args = sys.argv[1:]
    topic = "notes"
    if "--topic" in args:
        idx = args.index("--topic")
        if idx + 1 < len(args):
            topic = args[idx + 1]
            args = args[:idx] + args[idx + 2 :]

    content = " ".join(args).strip()
    if not content:
        print("Error: Empty note content.", file=sys.stderr)
        return 2

    filename = sanitize_topic(topic)
    os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
    target_path = os.path.join(KNOWLEDGE_DIR, filename)

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    entry_line = f"- [{now_str}] {content}\n"

    # If new file, add top-level heading
    is_new = not os.path.exists(target_path) or os.path.getsize(target_path) == 0

    with open(target_path, "a", encoding="utf-8") as f:
        if is_new:
            f.write(f"# Knowledge Notes: {filename[:-3].replace('-', ' ').title()}\n\n## Entries\n\n")
        f.write(entry_line)

    print(f"Appended note to {target_path}")

    # Trigger re-index
    script_dir = os.path.dirname(os.path.abspath(__file__))
    index_script = os.path.join(script_dir, "kb-index.py")
    if os.path.exists(index_script):
        print("Re-indexing knowledge base...")
        res = subprocess.run([sys.executable, index_script], capture_output=True, text=True)
        if res.returncode == 0:
            print("Knowledge base re-indexed successfully.")
            if res.stdout.strip():
                print(res.stdout.strip())
        else:
            print(f"Warning: Re-indexing encountered an issue: {res.stderr.strip()}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
