"""Shared helpers for the local knowledge-base scripts (kb-index / kb-search).

Uses Cohere's hosted embedding API instead of a local model — QMD's local
GGUF embedding took ~5 minutes per query on this VM's CPU (verified, not a
config issue), while a hosted embedding call is a small HTTP request that
returns in under a second. Gemini was tried first and dropped (free tier
caps at 5 requests/minute — the same bottleneck that got Xu made the
room's hub instead of Chùa); Voyage AI second and dropped (its "free"
tokens are gated behind a minimum $5 real purchase). Cohere's trial key
needs no card, no purchase, and still gives 2000 requests/minute.

The actual similarity search runs locally: with only a few dozen chunks,
brute-force cosine similarity is instant, no vector database needed.
"""
import json
import math
import os
import urllib.error
import urllib.request

EMBED_URL = "https://api.cohere.com/v2/embed"
EMBED_MODEL = "embed-v4.0"
INDEX_PATH = os.path.expanduser("~/data/knowledge-index.json")


def load_cohere_key() -> str:
    key = os.environ.get("COHERE_API_KEY", "").strip()
    if key:
        return key

    # Check ~/.openclaw/secrets.env
    secrets_path = os.path.expanduser("~/.openclaw/secrets.env")
    if os.path.exists(secrets_path):
        try:
            with open(secrets_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("COHERE_API_KEY="):
                        return line.strip().split("=", 1)[1].strip().strip("'\"")
        except Exception:
            pass

    # Check repo root .env
    root_env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(root_env):
        try:
            with open(root_env, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("COHERE_API_KEY="):
                        return line.strip().split("=", 1)[1].strip().strip("'\"")
        except Exception:
            pass
    return ""


def embed_texts(texts: list[str], input_type: str = "search_document") -> list[list[float]]:
    if not texts:
        return []
    api_key = load_cohere_key()
    if not api_key:
        raise SystemExit("COHERE_API_KEY not set in environment, ~/.openclaw/secrets.env, or .env")

    # Cohere allows up to 96 texts per call
    all_embeddings: list[list[float]] = []
    batch_size = 96
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        body = json.dumps({
            "texts": batch,
            "model": EMBED_MODEL,
            "input_type": input_type,
            "embedding_types": ["float"],
        }).encode()
        req = urllib.request.Request(
            EMBED_URL,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
            all_embeddings.extend(data["embeddings"]["float"])
        except urllib.error.HTTPError as exc:
            raise SystemExit(f"embedding API error {exc.code}: {exc.read().decode()[:300]}") from exc
    return all_embeddings


def embed_text(text: str, input_type: str = "search_document") -> list[float]:
    return embed_texts([text], input_type=input_type)[0]


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def chunk_markdown(text: str, max_chars: int = 1500) -> list[str]:
    """Split on '## ' headings; fall back to paragraph chunks if a section
    is still too long. Good enough for note-sized files, not a general
    chunker."""
    sections = []
    current = []
    for line in text.splitlines():
        if line.startswith("## ") and current:
            sections.append("\n".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        sections.append("\n".join(current))

    chunks = []
    for section in sections:
        if len(section) <= max_chars:
            if section.strip():
                chunks.append(section)
            continue
        paras = section.split("\n\n")
        buf = ""
        for para in paras:
            if len(buf) + len(para) > max_chars and buf:
                chunks.append(buf)
                buf = para
            else:
                buf = f"{buf}\n\n{para}" if buf else para
        if buf.strip():
            chunks.append(buf)
    return chunks


def load_index() -> list[dict]:
    if not os.path.exists(INDEX_PATH):
        return []
    with open(INDEX_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_index(entries: list[dict]) -> None:
    os.makedirs(os.path.dirname(INDEX_PATH), exist_ok=True)
    tmp_path = f"{INDEX_PATH}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False)
    os.replace(tmp_path, INDEX_PATH)
