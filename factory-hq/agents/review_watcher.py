"""Review Watcher — flags negative/urgent reviews needing a reply.

Deterministic checker (no LLM needed): reads reviews_sample.json and flags
1-2 star reviews or complaint keywords. Flagged reviews propose a reply
task in the approval queue with an honest reply template.
"""
import json
import os

from agents.learn import get_lessons, log_run

NAME = "review_watcher"
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REVIEWS_FILE = os.path.join(BASE, "reviews_sample.json")

COMPLAINT_WORDS = ["refund", "scam", "terrible", "disappointed", "angry",
                   "wrong", "broken", "never"]


def run():
    lessons = get_lessons(NAME)
    with open(REVIEWS_FILE, encoding="utf-8") as f:
        reviews = json.load(f)

    flagged = []
    for r in reviews:
        low = r.get("text", "").lower()
        bad_words = [w for w in COMPLAINT_WORDS if w in low]
        if r.get("stars", 5) <= 2 or bad_words:
            flagged.append({
                "source": r.get("source"), "stars": r.get("stars"),
                "text": r.get("text"),
                "urgent": r.get("stars", 5) == 1,
                "why": f"{r.get('stars')} stars" +
                       (f", keywords: {bad_words}" if bad_words else ""),
            })

    run_id = log_run(NAME, f"scan {len(reviews)} reviews",
                     f"{len(flagged)} need a reply")
    proposed = []
    for fl in flagged:
        proposed.append({
            "title": (f"{'URGENT ' if fl['urgent'] else ''}Reply needed: "
                     f"{fl['stars']}-star review on {fl['source']}"),
            "kind": "marketing",
            "detail": (f"Review: \"{fl['text']}\"\nFlagged: {fl['why']}\n"
                       "Suggested reply: \"Thank you for telling us - we're sorry "
                       "about this. Please message us so we can make it right.\""),
        })
    return {
        "ok": True,
        "summary": f"Scanned {len(reviews)} reviews, {len(flagged)} need a reply",
        "details": {"flagged": flagged, "run_id": run_id,
                    "lessons_seen": lessons["outcomes_seen"]},
        "proposed_approvals": proposed,
    }
