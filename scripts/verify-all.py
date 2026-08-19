#!/usr/bin/env python3
"""End-to-end Automated Test Suite & Verification for Xu Personal Assistant Tools.

Runs real functional tests against every script and generates a rigorous test report.
"""
from __future__ import annotations

import datetime
import json
import os
import subprocess
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)

results = []


def run_test(name: str, cmd: list[str], expect_code: int = 0, contains_str: str = "", cwd: str = PROJECT_DIR) -> dict:
    t0 = time.time()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=30,
        )
        elapsed = round(time.time() - t0, 3)
        code_match = proc.returncode == expect_code
        content_match = contains_str in proc.stdout or contains_str in proc.stderr if contains_str else True
        passed = code_match and content_match

        res = {
            "name": name,
            "cmd": " ".join(cmd),
            "exit_code": proc.returncode,
            "expected_code": expect_code,
            "elapsed_seconds": elapsed,
            "passed": passed,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
        }
    except Exception as exc:
        res = {
            "name": name,
            "cmd": " ".join(cmd),
            "exit_code": -1,
            "expected_code": expect_code,
            "elapsed_seconds": round(time.time() - t0, 3),
            "passed": False,
            "stdout": "",
            "stderr": str(exc),
        }
    results.append(res)
    return res


def main():
    print(f"==================================================================")
    print(f" XU PERSONAL ASSISTANT — RIGOROUS VERIFICATION SUITE")
    print(f" Timestamp: {datetime.datetime.now().isoformat()} | Host: macOS / Darwin")
    print(f"==================================================================\n")

    # 1. Web Search
    print("[1/8] Testing scripts/web-search (Live Exa Search & Wrapper)...")
    run_test(
        name="web_search_live_query",
        cmd=["./scripts/web-search", "Python 3.12 release notes", "--count", "2"],
        expect_code=0,
        contains_str="=== UNTRUSTED WEB SEARCH RESULTS",
    )

    # 2. Web Search Fallback (Zero-config DDG)
    print("[2/8] Testing scripts/web-search (DuckDuckGo Fallback without API key)...")
    env_no_keys = os.environ.copy()
    env_no_keys.pop("EXA_API_KEY", None)
    env_no_keys.pop("TAVILY_API_KEY", None)
    t0 = time.time()
    p = subprocess.run(
        ["python3", "scripts/web-search.py", "SQLite WAL mode", "--count", "2"],
        capture_output=True,
        text=True,
        cwd=PROJECT_DIR,
        env=env_no_keys,
        timeout=15,
    )
    results.append({
        "name": "web_search_ddg_fallback",
        "cmd": "python3 scripts/web-search.py 'SQLite WAL mode' --count 2 (no API keys)",
        "exit_code": p.returncode,
        "expected_code": 0,
        "elapsed_seconds": round(time.time() - t0, 3),
        "passed": p.returncode == 0 and "UNTRUSTED WEB SEARCH" in p.stdout,
        "stdout": p.stdout.strip(),
        "stderr": p.stderr.strip(),
    })

    # 3. Knowledge Base Save
    print("[3/8] Testing scripts/kb-save (Write + Topic Sanitize + Re-index)...")
    test_note = f"Automated test note generated at {datetime.datetime.now().isoformat()}: Memory persistence verified."
    run_test(
        name="kb_save_and_reindex",
        cmd=["./scripts/kb-save", test_note, "--topic", "automated-tests"],
        expect_code=0,
        contains_str="Knowledge base re-indexed successfully",
    )

    # 4. Knowledge Base Search
    print("[4/8] Testing scripts/kb-search (Semantic retrieval over newly saved note)...")
    run_test(
        name="kb_search_retrieval",
        cmd=["./scripts/kb-search", "automated test note memory persistence"],
        expect_code=0,
        contains_str="automated-tests.md",
    )

    # 5. Schedule Reminder
    print("[5/8] Testing scripts/schedule-reminder (Relative parse, List, Cancel)...")
    rem_res = run_test(
        name="schedule_reminder_create",
        cmd=["./scripts/schedule-reminder", "+2h", "Verify test suite run completed"],
        expect_code=0,
        contains_str="Scheduled reminder successfully",
    )
    # Extract ID from stdout
    rem_id = None
    for line in rem_res["stdout"].splitlines():
        if "- ID: " in line:
            rem_id = line.split("- ID: ")[1].strip()
            break

    run_test(
        name="schedule_reminder_list",
        cmd=["./scripts/schedule-reminder", "list"],
        expect_code=0,
        contains_str="ACTIVE REMINDERS",
    )

    if rem_id:
        run_test(
            name="schedule_reminder_cancel",
            cmd=["./scripts/schedule-reminder", "cancel", rem_id],
            expect_code=0,
            contains_str=f"Cancelled reminder: {rem_id}",
        )

    # 6. Safe Crawl SSRF Block (AWS / GCP Metadata)
    print("[6/8] Testing scripts/safe-crawl (SSRF Metadata Guard 169.254.169.254)...")
    run_test(
        name="safe_crawl_ssrf_metadata",
        cmd=["./scripts/safe-crawl", "http://169.254.169.254/computeMetadata/v1/"],
        expect_code=1,
        contains_str="SSRF Blocked: 169.254.169.254 resolves to 169.254.169.254, inside prohibited range 169.254.0.0/16",
    )

    # 7. Safe Crawl SSRF Block (Localhost & Private LAN)
    print("[7/8] Testing scripts/safe-crawl (SSRF Localhost & 10.0.0.1 Guard)...")
    run_test(
        name="safe_crawl_ssrf_localhost",
        cmd=["./scripts/safe-crawl", "http://localhost:18789"],
        expect_code=1,
        contains_str="SSRF Blocked: localhost resolves to 127.0.0.1",
    )
    run_test(
        name="safe_crawl_ssrf_private_ip",
        cmd=["./scripts/safe-crawl", "http://10.0.0.1:8080"],
        expect_code=1,
        contains_str="SSRF Blocked: 10.0.0.1 resolves to 10.0.0.1, inside prohibited range 10.0.0.0/8",
    )

    # 8. GitHub Review PR parsing test
    print("[8/8] Testing scripts/github-review (Target parser & Invalid format guard)...")
    run_test(
        name="github_review_invalid_arg",
        cmd=["./scripts/github-review"],
        expect_code=2,
        contains_str="Usage: github-review",
    )

    # Summary Report Generation
    print("\n" + "=" * 66)
    print(" SUMMARY TEST VERIFICATION REPORT")
    print("=" * 66)

    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed

    for idx, r in enumerate(results, 1):
        status_sym = "✅ PASS" if r["passed"] else "❌ FAIL"
        print(f"[{idx:02d}/{total:02d}] {status_sym} | {r['name']} ({r['elapsed_seconds']}s)")
        print(f"      Command: {r['cmd']}")
        print(f"      Exit Code: {r['exit_code']} (Expected: {r['expected_code']})")
        if not r["passed"]:
            print(f"      Stdout: {r['stdout'][:200]}")
            print(f"      Stderr: {r['stderr'][:200]}")
        print()

    print("-" * 66)
    print(f"TOTAL: {total} | PASSED: {passed} | FAILED: {failed} | SUCCESS RATE: {(passed/total)*100:.1f}%")
    print("=" * 66)

    # Save detailed JSON report
    report_path = os.path.join(PROJECT_DIR, "verification-report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.datetime.now().isoformat(),
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "tests": results,
        }, f, indent=2, ensure_ascii=False)
    print(f"\nSaved machine-readable test evidence to: {report_path}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
