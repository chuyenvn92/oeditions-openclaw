#!/usr/bin/env python3
"""Schedule ad-hoc reminders and follow-up tasks for Xu.

Usage:
    scripts/schedule-reminder "<time_spec>" "<reminder message>"
    scripts/schedule-reminder list
    scripts/schedule-reminder cancel <reminder_id>

Time specifications supported:
    +15m, +30m, +1h, +3h, +2d (Relative offsets)
    "2026-08-20 09:00" or "YYYY-MM-DD HH:MM" (Absolute time)
    "tomorrow 08:30", "today 17:00"

Storage:
    ~/data/reminders.json (Atomic updates)
"""
from __future__ import annotations

import datetime
import json
import os
import re
import sys
import uuid

REMINDERS_FILE = os.path.expanduser("~/data/reminders.json")


def load_reminders() -> list[dict]:
    if not os.path.exists(REMINDERS_FILE):
        return []
    try:
        with open(REMINDERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_reminders(items: list[dict]) -> None:
    os.makedirs(os.path.dirname(REMINDERS_FILE), exist_ok=True)
    tmp = f"{REMINDERS_FILE}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    os.replace(tmp, REMINDERS_FILE)


def parse_time_spec(spec: str) -> datetime.datetime:
    spec = spec.strip().lower()
    now = datetime.datetime.now()

    # Relative +15m, +1h, +2d
    rel_match = re.match(r"^\+?(\d+)\s*(m|min|mins|minutes|h|hr|hrs|hours|d|days?)$", spec)
    if rel_match:
        qty = int(rel_match.group(1))
        unit = rel_match.group(2)
        if unit.startswith("m"):
            return now + datetime.timedelta(minutes=qty)
        elif unit.startswith("h"):
            return now + datetime.timedelta(hours=qty)
        elif unit.startswith("d"):
            return now + datetime.timedelta(days=qty)

    # Tomorrow HH:MM
    if spec.startswith("tomorrow"):
        time_part = spec.replace("tomorrow", "").strip()
        target_date = (now + datetime.timedelta(days=1)).date()
        if time_part:
            t = datetime.datetime.strptime(time_part, "%H:%M").time()
            return datetime.datetime.combine(target_date, t)
        return datetime.datetime.combine(target_date, datetime.time(9, 0))

    # Today HH:MM
    if spec.startswith("today"):
        time_part = spec.replace("today", "").strip()
        t = datetime.datetime.strptime(time_part, "%H:%M").time()
        res = datetime.datetime.combine(now.date(), t)
        if res < now:
            res += datetime.timedelta(days=1)
        return res

    # Absolute YYYY-MM-DD HH:MM
    for fmt in ("%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M", "%d/%m/%Y %H:%M", "%H:%M"):
        try:
            parsed = datetime.datetime.strptime(spec, fmt)
            if fmt == "%H:%M":
                res = datetime.datetime.combine(now.date(), parsed.time())
                if res < now:
                    res += datetime.timedelta(days=1)
                return res
            return parsed
        except ValueError:
            pass

    raise ValueError(f"Could not parse time format: '{spec}'. Try '+30m', '+2h', or 'YYYY-MM-DD HH:MM'.")


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: schedule-reminder \"<time_spec>\" \"<message>\" | list | cancel <id>", file=sys.stderr)
        return 2

    cmd = sys.argv[1].strip()

    if cmd == "list":
        reminders = load_reminders()
        active = [r for r in reminders if r.get("status") == "pending"]
        if not active:
            print("No active pending reminders.")
            return 0
        print(f"=== ACTIVE REMINDERS ({len(active)}) ===")
        for r in sorted(active, key=lambda x: x["due_at"]):
            print(f"- ID: {r['id']} | Due: {r['due_at']} | Message: {r['message']}")
        print("=== END ACTIVE REMINDERS ===")
        return 0

    if cmd == "cancel":
        if len(sys.argv) < 3:
            print("Usage: schedule-reminder cancel <reminder_id>", file=sys.stderr)
            return 2
        rem_id = sys.argv[2].strip()
        reminders = load_reminders()
        found = False
        for r in reminders:
            if r["id"] == rem_id or r["id"].startswith(rem_id):
                r["status"] = "cancelled"
                found = True
                break
        if found:
            save_reminders(reminders)
            print(f"Cancelled reminder: {rem_id}")
            return 0
        print(f"Reminder not found: {rem_id}", file=sys.stderr)
        return 1

    # Create reminder: schedule-reminder <time_spec> <message>
    if len(sys.argv) < 3:
        print("Usage: schedule-reminder \"<time_spec>\" \"<message>\"", file=sys.stderr)
        return 2

    time_spec = sys.argv[1]
    message = " ".join(sys.argv[2:]).strip()

    try:
        due_datetime = parse_time_spec(time_spec)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    rem_id = f"rem_{int(due_datetime.timestamp())}_{uuid.uuid4().hex[:6]}"
    now_iso = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    due_iso = due_datetime.strftime("%Y-%m-%d %H:%M:%S")

    new_entry = {
        "id": rem_id,
        "created_at": now_iso,
        "due_at": due_iso,
        "message": message,
        "status": "pending",
    }

    reminders = load_reminders()
    reminders.append(new_entry)
    save_reminders(reminders)

    print(f"Scheduled reminder successfully!")
    print(f"- ID: {rem_id}")
    print(f"- Due: {due_iso} ({time_spec})")
    print(f"- Message: {message}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
