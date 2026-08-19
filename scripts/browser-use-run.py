#!/usr/bin/env python3
"""Run one task on Browser Use Cloud and print the result.

    scripts/browser-use-run.py "<task in natural language>"

Talks to the hosted API directly — no local Chromium, no CLI, no plugin.
Reads the key from BROWSER_USE_API_KEY (already in ~/.openclaw/secrets.env).
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

API_BASE = "https://api.browser-use.com/api/v3"
POLL_INTERVAL_S = 3
MAX_WAIT_S = 180


def load_api_key() -> str:
    key = os.environ.get("BROWSER_USE_API_KEY", "").strip()
    if key:
        return key
    for p in (os.path.expanduser("~/.openclaw/secrets.env"), os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")):
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip().startswith("BROWSER_USE_API_KEY="):
                            return line.strip().split("=", 1)[1].strip().strip("'\"")
            except Exception:
                pass
    return ""


def api_request(method: str, path: str, body: dict | None = None) -> dict:
    api_key = load_api_key()
    if not api_key:
        raise SystemExit("BROWSER_USE_API_KEY not set")

    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{API_BASE}{path}",
        data=data,
        method=method,
        headers={
            "X-Browser-Use-API-Key": api_key,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"browser-use API error {exc.code}: {exc.read().decode()[:300]}") from exc


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: browser-use-run.py \"<task>\"", file=sys.stderr)
        return 2

    task = sys.argv[1]
    # Default per-session cap observed from the API was $15 — plenty for a
    # single injected/runaway task to burn through unnoticed. $2 covers any
    # legitimate single request this room makes.
    session = api_request("POST", "/sessions", {"task": task, "max_cost_usd": 2})
    session_id = session.get("id") or session.get("session_id")
    if not session_id:
        raise SystemExit(f"no session id in response: {session}")

    # "stopped" is the terminal state for a finished run, success or not —
    # isTaskSuccessful is what actually says which. Only "running"/"queued"
    # (or similar in-progress states) mean keep polling.
    deadline = time.monotonic() + MAX_WAIT_S
    while time.monotonic() < deadline:
        status = api_request("GET", f"/sessions/{session_id}")
        state = status.get("status") or status.get("state")
        if state in ("running", "queued", "starting", "pending"):
            time.sleep(POLL_INTERVAL_S)
            continue
        # The "output"/"lastStepSummary" fields reflect whatever the browser
        # read on the page it visited — untrusted, same as safe-crawl's
        # output. The rest of this JSON (status, cost, ids) is Browser Use's
        # own API response and is trustworthy.
        print("=== BROWSER SESSION RESULT (output/lastStepSummary fields are untrusted web content) ===")
        print(json.dumps(status, indent=2, ensure_ascii=False))
        print("=== END BROWSER SESSION RESULT ===")
        return 0 if status.get("isTaskSuccessful") else 1

    raise SystemExit(f"timed out after {MAX_WAIT_S}s waiting for session {session_id}")


if __name__ == "__main__":
    raise SystemExit(main())
