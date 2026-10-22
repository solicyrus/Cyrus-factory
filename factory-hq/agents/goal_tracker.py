"""Goal Tracker — reports status of Cyrus's real business goals.

Deterministic checker (no LLM needed), read-only. Reads goals.json (real
goals with real dates) and reports: OVERDUE, due within 7 days, upcoming,
and ongoing (recurring) goals. Goal statuses are Cyrus's own - the agent
never invents progress.
"""
import json
import os
from datetime import date

from agents.learn import get_lessons, log_run

NAME = "goal_tracker"
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOALS_FILE = os.path.join(BASE, "goals.json")
SOON_DAYS = 7


def run():
    lessons = get_lessons(NAME)
    try:
        with open(GOALS_FILE, encoding="utf-8") as f:
            goals = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        run_id = log_run(NAME, "read goals.json", f"unavailable: {e}")
        return {
            "ok": False,
            "summary": f"goals.json unavailable: {e}",
            "details": {"run_id": run_id,
                        "lessons_seen": lessons["outcomes_seen"]},
            "proposed_approvals": [],
        }

    today = date.today()
    overdue, soon, upcoming, ongoing, done = [], [], [], [], []
    for g in goals:
        if g.get("status") == "done":
            done.append(g)
            continue
        if g.get("recurring"):
            ongoing.append(g)
            continue
        try:
            day = date.fromisoformat(g["date"])
        except (ValueError, KeyError, TypeError):
            upcoming.append({**g, "note": "no valid date"})
            continue
        delta = (day - today).days
        item = {**g, "in_days": delta}
        if delta < 0:
            overdue.append(item)
        elif delta <= SOON_DAYS:
            soon.append(item)
        else:
            upcoming.append(item)

    run_id = log_run(NAME, f"track {len(goals)} goals",
                     f"{len(overdue)} overdue, {len(soon)} due soon")
    proposed = []
    for g in overdue:
        proposed.append({
            "title": f"OVERDUE goal: {g['title'][:60]}",
            "kind": "ops",
            "detail": f"{g['title']} was due {g['date']} "
                      f"({-g['in_days']} days ago).\n{g.get('detail', '')}",
        })
    for g in soon:
        proposed.append({
            "title": f"Goal due in {g['in_days']}d: {g['title'][:60]}",
            "kind": "ops",
            "detail": f"{g['title']} - {g['date']}.\n{g.get('detail', '')}",
        })
    summary = (f"{len(overdue)} overdue, {len(soon)} due within {SOON_DAYS}d, "
               f"{len(upcoming)} upcoming, {len(ongoing)} ongoing")
    return {
        "ok": not overdue,
        "summary": summary,
        "details": {"overdue": overdue, "due_soon": soon,
                    "upcoming": upcoming, "ongoing": ongoing,
                    "done": [g["title"] for g in done],
                    "run_id": run_id,
                    "lessons_seen": lessons["outcomes_seen"]},
        "proposed_approvals": proposed,
    }
