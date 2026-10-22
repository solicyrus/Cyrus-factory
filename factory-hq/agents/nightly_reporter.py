"""Nightly Reporter — composes the nightly Persian business summary draft.

Judgment agent: reads the factory activity log (factory_state.json) and
drafts the short Persian summary Cyrus sends on. LLM when keys are set,
template fallback otherwise. Draft goes to the approval queue - Cyrus
always reviews before anything is sent.
"""
import json
import os

from agents.learn import get_lessons, log_run
from agents.llm import ask as llm_ask

NAME = "nightly_reporter"

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_FILE = os.path.join(BASE, "factory_state.json")


def _read_activity(limit=10):
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            state = json.load(f)
        return state.get("activity", [])[:limit]
    except Exception:
        return []


def _rule_based(activity):
    lines = ["خلاصه امشب کارخونه:"]
    if not activity:
        lines.append("- امروز فعالیتی ثبت نشده.")
    for a in activity[:8]:
        lines.append(f"- {a.get('actor', '?')}: {a.get('text', '')[:90]}")
    lines.append("به امید خدا فردا ادامه می‌دیم.")
    return "\n".join(lines)


def run():
    lessons = get_lessons(NAME)
    activity = _read_activity()
    activity_text = "\n".join(
        f"- {a.get('actor', '?')}: {a.get('text', '')}" for a in activity) \
        or "(no activity logged today)"

    prompt = (
        "Write a short nightly business summary in Persian (Farsi) from this "
        "factory activity log. Max 12 lines. Format: ✅ done / 👀 waiting / "
        "📌 open items. Simple words, warm tone, no personal details.\n\n"
        f"Activity log:\n{activity_text}"
    )
    text = llm_ask(prompt, system="You write short Persian business summaries.",
                   max_tokens=500)
    mode = "llm"
    summary = " ".join(text.split()) if text else ""
    if len(summary) < 40:
        summary = _rule_based(activity)
        mode = "rule-based"

    run_id = log_run(NAME, f"summarize {len(activity)} activity entries",
                     f"{mode}: {summary[:150]}")
    return {
        "ok": True,
        "summary": f"Nightly Persian summary drafted ({mode})",
        "details": {"summary": summary, "mode": mode, "run_id": run_id,
                    "activity_entries": len(activity),
                    "lessons_seen": lessons["outcomes_seen"]},
        "proposed_approvals": [{
            "title": "Nightly Persian business summary (draft)",
            "kind": "report",
            "detail": summary,
        }],
    }
