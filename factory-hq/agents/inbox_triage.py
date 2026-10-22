"""Inbox Triage — classifies inbox items into urgent / can-wait / ignore.

Deterministic checker (no LLM needed): reads inbox_sample.json and applies
keyword rules. Urgent items (security, money, refunds) propose an approval
so Cyrus sees them in the queue.
"""
import json
import os

from agents.learn import get_lessons, log_run

NAME = "inbox_triage"
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INBOX_FILE = os.path.join(BASE, "inbox_sample.json")

URGENT_WORDS = ["login code", "secure your account", "payment failed",
                "refund", "declined", "suspicious"]
IGNORE_WORDS = ["newsletter", "promo", "trends", "unsubscribe", "roundup"]


def _classify(item):
    text = (item.get("subject", "") + " " + item.get("body", "")).lower()
    if any(w in text for w in URGENT_WORDS):
        return "urgent"
    if any(w in text for w in IGNORE_WORDS):
        return "ignore"
    return "can-wait"


def run():
    lessons = get_lessons(NAME)
    with open(INBOX_FILE, encoding="utf-8") as f:
        items = json.load(f)

    triaged = []
    for it in items:
        triaged.append({"from": it.get("from"), "subject": it.get("subject"),
                        "class": _classify(it)})

    urgent = [t for t in triaged if t["class"] == "urgent"]
    run_id = log_run(NAME, f"triage {len(items)} inbox items",
                     f"{len(urgent)} urgent, "
                     f"{sum(1 for t in triaged if t['class'] == 'can-wait')} can-wait, "
                     f"{sum(1 for t in triaged if t['class'] == 'ignore')} ignore")
    proposed = []
    if urgent:
        proposed.append({
            "title": f"Inbox triage: {len(urgent)} urgent item(s) need you",
            "kind": "ops",
            "detail": "\n".join(f"- {u['from']}: {u['subject']}" for u in urgent),
        })
    return {
        "ok": True,
        "summary": (f"Triaged {len(items)} items: {len(urgent)} urgent"),
        "details": {"triaged": triaged, "run_id": run_id,
                    "lessons_seen": lessons["outcomes_seen"]},
        "proposed_approvals": proposed,
    }
