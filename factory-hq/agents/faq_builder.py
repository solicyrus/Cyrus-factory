"""FAQ Builder — drafts 3 FAQ entries (question + honest short answer).

Creative agent: LLM when keys are set, rule-based fallback otherwise.
Answers must be honest: real prices only, no invented policies.
Draft goes to the approval queue.
"""
import re

from agents.learn import get_lessons, log_run
from agents.llm import ask as llm_ask

NAME = "faq_builder"

FACTS = (
    "Cyrus AI Tour Guide: CA$10 / 14 days unlimited trip planning (website bot). "
    "Cyrus AI app: CA$5 one-time unlock, North America trip planner. "
    "Cyrus AI Premium: $79/trip, human Guardian Angel. The bot gives travel "
    "information only - the traveler books everything themselves, directly."
)

FALLBACK_FAQS = [
    ("How much does Cyrus AI cost?",
     "CA$10 for 14 days of unlimited trip planning on the website. "
     "The app is a CA$5 one-time unlock. Premium with a human helper is $79 per trip."),
    ("Does Cyrus AI book hotels and tours for me?",
     "No - it plans everything (places, hotels, transport, hour by hour) and you "
     "book directly with the providers. That keeps prices honest and up to date."),
    ("What if I don't like the plan?",
     "Tell the bot what to change and it rebuilds the plan with you, "
     "in your language, until it fits."),
]


def _parse_faqs(text):
    faqs = []
    for line in text.splitlines():
        m = re.match(r"\s*\d+[.)]\s*(.+)", line)
        if m and "?" in m.group(1):
            faqs.append(m.group(1).strip())
    return faqs


def run():
    lessons = get_lessons(NAME)
    notes = lessons.get("rejected_notes", [])
    hint = ("Avoid these previously rejected angles: " + "; ".join(notes)
            if notes else "No past feedback yet.")

    prompt = (
        f"Write 3 FAQ entries for this product. Facts (never invent others):\n"
        f"{FACTS}\n\n{hint}\n\nEach on ONE numbered line: question? - short honest answer. "
        "Answers under 35 words. Never invent prices, policies or guarantees."
    )
    text = llm_ask(prompt, system="You write honest, short FAQ entries.",
                   max_tokens=400)
    mode = "llm"
    faqs = _parse_faqs(text) if text else []
    if len(faqs) < 2:
        faqs = [f"{q} - {a}" for q, a in FALLBACK_FAQS]
        mode = "rule-based"

    run_id = log_run(NAME, "draft 3 FAQ entries",
                     f"{mode}: " + " | ".join(faqs)[:350])
    return {
        "ok": True,
        "summary": f"3 FAQ entries drafted ({mode})",
        "details": {"faqs": faqs, "mode": mode, "run_id": run_id,
                    "lessons_seen": lessons["outcomes_seen"]},
        "proposed_approvals": [{
            "title": "New FAQ entries from FAQ Builder",
            "kind": "support",
            "detail": "\n\n".join(f"{n + 1}. {f}" for n, f in enumerate(faqs)),
        }],
    }
