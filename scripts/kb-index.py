#!/usr/bin/env python3
"""Index every .md file in ~/data/knowledge/ for kb-search.py.

    scripts/kb-index.py

Re-run after adding/changing files in that directory. Cheap: ~12 files,
a few dozen chunks, one small API call per chunk.
"""
import glob
import os
import sys

from kb_common import chunk_markdown, embed_texts, save_index

KNOWLEDGE_DIR = os.path.expanduser("~/data/knowledge")


def main() -> int:
    files = sorted(glob.glob(os.path.join(KNOWLEDGE_DIR, "*.md")))
    if not files:
        print(f"no .md files in {KNOWLEDGE_DIR}", file=sys.stderr)
        return 1

    chunk_data = []
    for path in files:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        chunks = chunk_markdown(text)
        for i, chunk in enumerate(chunks):
            chunk_data.append({
                "file": os.path.basename(path),
                "chunk_index": i,
                "text": chunk,
            })

    if not chunk_data:
        save_index([])
        print("Indexed 0 chunks (empty files)")
        return 0

    texts = [c["text"] for c in chunk_data]
    vectors = embed_texts(texts, input_type="search_document")

    entries = []
    for c, vec in zip(chunk_data, vectors):
        entries.append({
            "file": c["file"],
            "chunk_index": c["chunk_index"],
            "text": c["text"],
            "vector": vec,
        })

    save_index(entries)
    print(f"indexed {len(entries)} chunks from {len(files)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
