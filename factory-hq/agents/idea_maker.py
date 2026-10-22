"""Idea Maker — generates 3 concrete business ideas for the tour business.

Creative agent: uses the shared LLM backend when keys are set, otherwise a
deterministic rule-based set. Past rejections (from get_lessons) steer both
paths away from angles Cyrus already dismissed. The draft goes to the
approval queue - nothing is acted on without his approve click.
"""
import re

from agents.learn import get_lessons, log_run
from agents.llm import ask as llm_ask

NAME = "idea_maker"

BUSINESS = (
    "Victoria Tour and Adventure - AI-only business. Products: Cyrus AI Tour Guide "
    "(website bot, CA$10 / 14 days unlimited trip planning), Cyrus AI app (CA$5 one-time, "
    "North America trip planner), Cyrus AI Premium ($79/trip, human Guardian Angel). "
    "Audience: travelers to Canada + USA. Marketing: YouTube Shorts 3x/week."
)

FALLBACK_IDEAS = [
    ("Hotel-partner QR cards: 'Plan your Victoria stay with Cyrus AI'",
     "Hotels want happy guests; a QR at reception turns foot traffic into CA$10 plans.",
     "Draft a one-page partner offer and send it to 5 downtown Victoria hotels."),
    ("Premium $79 upsell inside the CA$10 chat",
     "Planners who hit a hard question convert to Guardian Angel human help.",
     "Add one honest upsell line after day 3 of a 14-day plan."),
    ("Shorts funnel: 'We planned this trip in 60 seconds'",
     "3 Shorts/week already run; each ends with the CA$10 CTA.",
     "Next Short shows a real 2-day Banff plan built by Cyrus AI."),
]


def _rule_based(lessons):
    banned_words = set()
    for note in lessons.get("rejected_notes", []):
        banned_words.update(w for w in re.findall(r"[a-z]{5,}", note.lower()))
    ideas = [i for i in FALLBACK_IDEAS
             if not banned_words.intersection(i[0].lower().split())]
    return ideas or FALLBACK_IDEAS


def _parse_numbered(text):
    items = []
    for line in text.splitlines():
        m = re.match(r"\s*\d+[.)]\s*(.+)", line)
        if m and len(m.group(1).strip()) > 10:
            items.append(m.group(1).strip())
    return items


def run():
    lessons = get_lessons(NAME)
    notes = lessons.get("rejected_notes", [])
    hint = ("Avoid these previously rejected angles: " + "; ".join(notes)
            if notes else "No past feedback yet - all angles are fresh.")

    prompt = (
        f"You are a business idea generator for this business:\n{BUSINESS}\n\n"
        f"{hint}\n\nGive exactly 3 concrete, low-cost business ideas. "
        "Each on ONE numbered line: title - why it works - first step. "
        "Keep each under 40 words. No hype, no fake numbers, no invented prices."
    )
    text = llm_ask(prompt,
                   system="You give short, practical business ideas.",
                   max_tokens=400)
    mode = "llm"
    ideas = _parse_numbered(text) if text else []
    if len(ideas) < 2:
        ideas = [f"{t} - {w} First step: {s}"
                 for t, w, s in _rule_based(lessons)]
        mode = "rule-based"

    run_id = log_run(NAME, "generate 3 business ideas",
                     f"{mode}: " + " | ".join(ideas)[:350])
    return {
        "ok": True,
        "summary": f"3 business ideas drafted ({mode})",
        "details": {"ideas": ideas, "mode": mode, "run_id": run_id,
                    "lessons_seen": lessons["outcomes_seen"]},
        "proposed_approvals": [{
            "title": "New business ideas from Idea Maker",
            "kind": "idea",
            "detail": "\n\n".join(f"{n + 1}. {d}"
                                  for n, d in enumerate(ideas)),
        }],
    }
