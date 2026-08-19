#!/usr/bin/env python3
"""Search the local knowledge base.

    scripts/kb-search.py "<question>"

Embeds the query via the same hosted API used to build the index, then
ranks stored chunks by cosine similarity — no local model, no GPU, just
one small HTTP call plus a dot product over however many chunks exist.
"""
import sys

from kb_common import cosine, embed_text, load_index

TOP_N = 3


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: kb-search.py \"<question>\"", file=sys.stderr)
        return 2

    query = sys.argv[1]
    entries = load_index()
    if not entries:
        print("Index is empty — run kb-index.py first.", file=sys.stderr)
        return 1

    query_vector = embed_text(query, input_type="search_query")
    scored = sorted(
        entries,
        key=lambda e: cosine(query_vector, e["vector"]),
        reverse=True,
    )

    for entry in scored[:TOP_N]:
        score = cosine(query_vector, entry["vector"])
        print(f"--- {entry['file']} (score {score:.2f}) ---")
        print(entry["text"])
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
