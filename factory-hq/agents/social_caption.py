"""Social Caption — drafts an Instagram caption + hashtags.

Creative agent: uses the shared LLM backend when keys are set, otherwise a
deterministic rule-based caption. Honest by design: no fake claims, no
invented prices, real business facts only. The draft goes to the approval
queue - nothing is posted without Cyrus's approve click.
"""
import re

from agents.learn import get_lessons, log_run
from agents.llm import ask as llm_ask

NAME = "social_caption"
CTA = "Plan it with Cyrus AI 👇 victoriatourandadventure.com"
TAGS = "#VictoriaBC #VancouverIsland #ExploreBC #CanadaTravel #PacificNorthwest"


def _rule_based(topic):
    caption = (
        f"{topic.strip().title()} — Victoria, BC never disappoints 🇨🇦\n\n"
        f"Save this for your trip planning!\n\n{CTA}"
    )
    return {"caption": caption, "hashtags": TAGS}


def run(topic="sunset at Clover Point"):
    lessons = get_lessons(NAME)
    topic = (topic or "sunset at Clover Point").strip()
    notes = lessons.get("rejected_notes", [])
    hint = ("Avoid these previously rejected styles: " + "; ".join(notes)
            if notes else "No past feedback yet.")

    prompt = (
        f"Write an Instagram caption for a travel photo about: {topic}\n{hint}\n\n"
        "Rules: honest, no fake claims, no invented prices or hours, "
        "warm and short (under 60 words), end with a Cyrus AI trip-planning CTA.\n"
        "Then on a new line: HASHTAGS: 5 relevant hashtags.\n"
        "Format exactly:\nCAPTION: <text>\nHASHTAGS: <tags>"
    )
    text = llm_ask(prompt, system="You write Instagram captions for a tour business.",
                   max_tokens=250)
    mode, draft = "llm", None
    if text:
        cap_m = re.search(r"CAPTION:\s*(.+?)(?=HASHTAGS:|$)", text, re.S)
        tag_m = re.search(r"HASHTAGS:\s*(.+)", text, re.S)
        if cap_m:
            draft = {
                "caption": cap_m.group(1).strip(),
                "hashtags": " ".join(tag_m.group(1).split()) if tag_m else TAGS,
            }
    if not draft:
        draft = _rule_based(topic)
        mode = "rule-based"

    run_id = log_run(NAME, f"caption for '{topic}'",
                     f"{mode}: {draft['caption'][:60]}")
    return {
        "ok": True,
        "summary": f"Drafted Instagram caption for '{topic}' ({mode})",
        "details": {**draft, "run_id": run_id,
                    "lessons_seen": lessons["outcomes_seen"]},
        "proposed_approvals": [{
            "title": f"Instagram caption draft: {topic[:50]}",
            "kind": "content",
            "detail": f"{draft['caption']}\n\n{draft['hashtags']}\n"
                      "(Approve = ready for Cyrus to post from his phone)",
        }],
    }
