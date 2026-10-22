"""Content Writer — drafts YouTube Shorts metadata packs.

Creative agent: uses the shared LLM backend when keys are set, otherwise the
deterministic rule-based pack. Reads past lessons first: if Cyrus rejected a
draft with this topic/slug before, the title is reworked instead of repeated.
The draft goes to the factory approval queue - nothing is published without
Cyrus's approve click.
"""
import re

from agents.learn import get_lessons, log_run
from agents.llm import ask as llm_ask

NAME = "content_writer"

CTA = "🌐 victoriatourandadventure.com"
BASE_TAGS = ["#VancouverIsland", "#BritishColumbia", "#ExploreBC",
             "#CanadaTravel", "#VictoriaBC"]


def _slug(topic):
    return re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")


def _rule_based_pack(topic):
    title = f"{topic.title()} ✨ | Victoria, BC #shorts"
    description = (
        f"{topic.title()} — one more reason Victoria, BC is unforgettable 🇨🇦\n\n"
        f"Want the perfect itinerary? Let Cyrus AI plan it hour by hour 👇\n"
        f"{CTA}"
    )
    return {"title": title, "description": description,
            "hashtags": " ".join(["#Shorts"] + BASE_TAGS),
            "slug": _slug(topic)}


def _was_rejected(lessons, text):
    """True if this exact draft text was rejected before."""
    for out in lessons.get("rejected_outputs", []):
        if text and text[:60] in out:
            return True
    return False


def run(topic="hidden gem in Victoria BC"):
    lessons = get_lessons(NAME)
    topic = (topic or "hidden gem in Victoria BC").strip()
    notes = lessons.get("rejected_notes", [])
    hint = ("Avoid these previously rejected angles: " + "; ".join(notes)
            if notes else "No past feedback yet.")

    prompt = (
        f"Write a YouTube Shorts metadata pack about: {topic}\n{hint}\n\n"
        "Format exactly:\nTITLE: <short hook title, ends with '#shorts'>\n"
        "DESCRIPTION: <2 lines, mention Victoria BC, end with a Cyrus AI trip-planning CTA>\n"
        "HASHTAGS: <#Shorts plus 4-5 relevant tags>\n"
        "Keep it honest, no clickbait, no fake claims."
    )
    text = llm_ask(prompt, system="You write YouTube Shorts metadata.",
                   max_tokens=300)
    mode = "llm"
    draft = None
    if text:
        title_m = re.search(r"TITLE:\s*(.+)", text)
        desc_m = re.search(r"DESCRIPTION:\s*(.+?)(?=HASHTAGS:|$)", text, re.S)
        tags_m = re.search(r"HASHTAGS:\s*(.+)", text, re.S)
        if title_m:
            draft = {
                "title": title_m.group(1).strip(),
                "description": (desc_m.group(1).strip() if desc_m else ""),
                "hashtags": " ".join(tags_m.group(1).split()) if tags_m
                            else " ".join(["#Shorts"] + BASE_TAGS),
                "slug": _slug(topic),
            }
    if not draft:
        draft = _rule_based_pack(topic)
        mode = "rule-based"

    # Learning in action: never repeat a rejected title verbatim
    if _was_rejected(lessons, draft["title"]):
        draft["title"] = draft["title"].replace("✨", "🌅") + " (fresh angle)"
        draft["slug"] += "-v2"

    run_id = log_run(NAME, f"Shorts pack for '{topic}'",
                     f"{mode}: {draft['title']}")
    return {
        "ok": True,
        "summary": f"Drafted Shorts pack for '{topic}' ({mode})",
        "details": {**draft, "run_id": run_id,
                    "lessons_seen": lessons["outcomes_seen"]},
        "proposed_approvals": [{
            "title": f"Publish Shorts draft: {draft['title'][:60]}",
            "kind": "content",
            "detail": (f"Title: {draft['title']}\n"
                       f"Description: {draft['description']}\n"
                       f"Hashtags: {draft['hashtags']}\n"
                       "(Approve = ready for Cyrus to upload from his phone)"),
        }],
    }
