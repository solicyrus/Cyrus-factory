"""Ads Angles — drafts 3 ad angles for Cyrus AI.

Creative agent: LLM when keys are set, rule-based fallback otherwise.
Past rejections steer away from dismissed angles. Draft goes to the
approval queue.
"""
import re

from agents.learn import get_lessons, log_run
from agents.llm import ask as llm_ask

NAME = "ads_angles"

PRODUCT = (
    "Cyrus AI Tour Guide - AI trip planner for Canada + USA. "
    "CA$10 / 14 days unlimited planning (website bot), CA$5 one-time app unlock, "
    "$79/trip Premium with a human Guardian Angel. Honest data: never invents "
    "prices, hours or phone numbers."
)

FALLBACK_ANGLES = [
    ("Your AI tour guide for North America",
     "CA$10 plans your whole 14-day trip hour by hour - places, hotels, transport."),
    ("Stop guessing. Get honest answers.",
     "Cyrus AI never invents prices or hours. Real data or an honest 'I don't know'."),
    ("Travel with a Guardian Angel",
     "$79/trip: a real human on call while Cyrus AI plans every detail."),
]


def _rule_based(lessons):
    banned_words = set()
    for note in lessons.get("rejected_notes", []):
        banned_words.update(w for w in re.findall(r"[a-z]{5,}", note.lower()))
    angles = [a for a in FALLBACK_ANGLES
              if not banned_words.intersection(a[0].lower().split())]
    return angles or FALLBACK_ANGLES


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
            if notes else "No past feedback yet.")

    prompt = (
        f"Write 3 short ad angles for this product:\n{PRODUCT}\n\n{hint}\n\n"
        "Each on ONE numbered line: headline - one-line body. "
        "Under 25 words each. Honest tone, no fake discounts, no invented claims."
    )
    text = llm_ask(prompt,
                   system="You write short honest ad copy.",
                   max_tokens=300)
    mode = "llm"
    angles = _parse_numbered(text) if text else []
    if len(angles) < 2:
        angles = [f"{h} - {b}" for h, b in _rule_based(lessons)]
        mode = "rule-based"

    run_id = log_run(NAME, "draft 3 ad angles",
                     f"{mode}: " + " | ".join(angles)[:350])
    return {
        "ok": True,
        "summary": f"3 ad angles drafted ({mode})",
        "details": {"angles": angles, "mode": mode, "run_id": run_id,
                    "lessons_seen": lessons["outcomes_seen"]},
        "proposed_approvals": [{
            "title": "New ad angles from Ads Angles",
            "kind": "marketing",
            "detail": "\n\n".join(f"{n + 1}. {a}"
                                  for n, a in enumerate(angles)),
        }],
    }
