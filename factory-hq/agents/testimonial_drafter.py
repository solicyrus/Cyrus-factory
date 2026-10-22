"""Testimonial Drafter — drafts a short review-request message.

Creative agent: LLM when keys are set, rule-based fallback otherwise.
Polite, short, never pushy, never offers incentives for reviews.
Draft goes to the approval queue.
"""
from agents.learn import get_lessons, log_run
from agents.llm import ask as llm_ask

NAME = "testimonial_drafter"

FALLBACK_MESSAGE = (
    "Hi! Glad Cyrus AI helped plan your trip. If you have a minute, "
    "an honest Google review means a lot to our small Victoria business. "
    "No pressure at all - and thank you for traveling with us!"
)


def run():
    lessons = get_lessons(NAME)
    notes = lessons.get("rejected_notes", [])
    hint = ("Avoid these previously rejected angles: " + "; ".join(notes)
            if notes else "No past feedback yet.")

    prompt = (
        "Write a short review-request message for a happy customer of "
        "'Cyrus AI Tour Guide' (AI trip planner, Victoria BC small business). "
        f"{hint}\n\nRules: under 50 words, warm and polite, never pushy, "
        "never offer discounts or incentives for reviews, English."
    )
    text = llm_ask(prompt, system="You write short polite customer messages.",
                   max_tokens=150)
    mode = "llm"
    message = " ".join(text.split()) if text else ""
    if len(message) < 30:
        message = FALLBACK_MESSAGE
        mode = "rule-based"

    run_id = log_run(NAME, "draft review-request message", f"{mode}: {message[:120]}")
    return {
        "ok": True,
        "summary": f"Review-request message drafted ({mode})",
        "details": {"message": message, "mode": mode, "run_id": run_id,
                    "lessons_seen": lessons["outcomes_seen"]},
        "proposed_approvals": [{
            "title": "Review-request message from Testimonial Drafter",
            "kind": "marketing",
            "detail": message,
        }],
    }
