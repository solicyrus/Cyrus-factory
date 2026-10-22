"""WhatsApp Drafter — drafts a short broadcast for the future business number.

Takes topic. Short, honest broadcast message about the tour business with
a Cyrus AI CTA. No fake urgency, no invented discounts, no false claims.
The draft goes to the approval queue - nothing is sent without Cyrus's
approve click. (The business WhatsApp number itself is not set up yet.)
"""
import re

from agents.learn import get_lessons, log_run
from agents.llm import ask as llm_ask

NAME = "whatsapp_drafter"
CTA = "👉 Plan your trip with Cyrus AI: victoriatourandadventure.com"


def _rule_based(topic):
    return (f"Hello from Victoria Tour and Adventure! 🌊\n\n"
            f"{topic.strip()}\n\n{CTA}")


def run(topic="New: Cyrus AI plans your North America trip hour by hour"):
    lessons = get_lessons(NAME)
    topic = (topic or "New: Cyrus AI plans your North America trip hour by hour").strip()
    notes = lessons.get("rejected_notes", [])
    hint = ("Avoid these previously rejected styles: " + "; ".join(notes)
            if notes else "No past feedback yet.")

    prompt = (
        f"Write a short WhatsApp broadcast message (under 50 words) about: {topic}\n"
        f"{hint}\n\nRules: honest, warm, no fake urgency, no invented "
        f"discounts, end with a Cyrus AI trip-planning CTA.\n"
        "Format exactly:\nMESSAGE: <text>"
    )
    text = llm_ask(prompt, system="You write WhatsApp broadcasts for a tour business.",
                   max_tokens=200)
    mode, message = "llm", None
    if text:
        m = re.search(r"MESSAGE:\s*(.+)", text, re.S)
        if m:
            message = m.group(1).strip()
    if not message:
        message = _rule_based(topic)
        mode = "rule-based"

    run_id = log_run(NAME, f"broadcast about '{topic[:40]}'", f"{mode}")
    return {
        "ok": True,
        "summary": f"Drafted WhatsApp broadcast ({mode})",
        "details": {"topic": topic, "message": message, "run_id": run_id,
                    "lessons_seen": lessons["outcomes_seen"]},
        "proposed_approvals": [{
            "title": f"WhatsApp broadcast draft: {topic[:50]}",
            "kind": "marketing",
            "detail": f"{message}\n"
                      "(Approve = draft only - business number not set up yet)",
        }],
    }
