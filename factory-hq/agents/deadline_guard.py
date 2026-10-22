"""Deadline Guard — lists business deadlines within 30 days.

Deterministic checker (no LLM needed): reads dates.json (real deadlines:
Play test end, bike room, business licence renewal, church site renewal)
and lists what is coming. Anything within 7 days proposes an urgent
approval so Cyrus never misses it.
"""
import json
import os
from datetime import date

from agents.learn import get_lessons, log_run

NAME = "deadline_guard"
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATES_FILE = os.path.join(BASE, "dates.json")

WARN_DAYS = 30
URGENT_DAYS = 7


def run():
    lessons = get_lessons(NAME)
    with open(DATES_FILE, encoding="utf-8") as f:
        deadlines = json.load(f)

    today = date.today()
    upcoming, urgent = [], []
    for d in deadlines:
        try:
            day = date.fromisoformat(d["date"])
        except ValueError:
            continue
        delta = (day - today).days
        if delta < 0:
            continue  # past
        item = {"title": d["title"], "date": d["date"], "in_days": delta}
        if delta <= WARN_DAYS:
            upcoming.append(item)
        if delta <= URGENT_DAYS:
            urgent.append(item)
    upcoming.sort(key=lambda x: x["in_days"])

    run_id = log_run(NAME, f"scan {len(deadlines)} deadlines",
                     f"{len(upcoming)} within {WARN_DAYS}d, {len(urgent)} urgent")
    proposed = []
    for u in urgent:
        proposed.append({
            "title": f"URGENT deadline in {u['in_days']} days: {u['title'][:60]}",
            "kind": "ops",
            "detail": f"{u['title']} - due {u['date']} ({u['in_days']} days left).",
        })
    detail_list = "\n".join(
        f"- {u['date']} ({u['in_days']}d): {u['title']}" for u in upcoming) \
        or "No deadlines within 30 days."
    return {
        "ok": True,
        "summary": f"{len(upcoming)} deadline(s) within 30 days, {len(urgent)} urgent",
        "details": {"upcoming": upcoming, "urgent": urgent, "run_id": run_id,
                    "lessons_seen": lessons["outcomes_seen"]},
        "proposed_approvals": proposed,
    }
