"""Shorts Planner — builds a 1-week YouTube Shorts calendar.

Deterministic planner (no LLM needed): computes the next Sat/Mon/Wed slots
(the channel's 3x/week cadence) and assigns title ideas, skipping topics
Cyrus rejected before. The calendar goes to the approval queue.
"""
from datetime import date, timedelta

from agents.learn import get_lessons, log_run

NAME = "shorts_planner"

TOPIC_POOL = [
    "Sunrise over the Victoria waterfront",
    "Hidden beaches of Vancouver Island",
    "Butchart Gardens in 30 seconds",
    "Whale watching near Victoria",
    "Old Town Victoria walking tour",
    "Best viewpoints around Victoria BC",
]


def _next_weekday(from_date, weekday):
    delta = (weekday - from_date.weekday()) % 7
    return from_date + timedelta(days=delta or 7)


def run():
    lessons = get_lessons(NAME)
    rejected = " ".join(lessons.get("rejected_notes", [])).lower()

    today = date.today()
    slots = [("Saturday", _next_weekday(today, 5)),
             ("Monday", _next_weekday(today, 0)),
             ("Wednesday", _next_weekday(today, 2))]
    slots.sort(key=lambda s: s[1])

    topics = [t for t in TOPIC_POOL
              if not any(w in t.lower() for w in rejected.split() if len(w) > 4)]
    topics = topics or TOPIC_POOL

    plan = []
    for i, (day, d) in enumerate(slots):
        topic = topics[i % len(topics)]
        plan.append({"day": day, "date": d.isoformat(),
                     "title": f"{topic} ✨ | Victoria, BC #shorts"})

    detail = "\n".join(f"{p['day']} {p['date']}: {p['title']}" for p in plan)
    run_id = log_run(NAME, "build 1-week Shorts calendar", detail[:300])
    return {
        "ok": True,
        "summary": f"Shorts calendar built: {', '.join(p['day'] for p in plan)}",
        "details": {"plan": plan, "run_id": run_id,
                    "lessons_seen": lessons["outcomes_seen"]},
        "proposed_approvals": [{
            "title": "Next week's Shorts calendar (Sat/Mon/Wed)",
            "kind": "content",
            "detail": detail + "\n(Film on phone, Cyrus edits and uploads.)",
        }],
    }
