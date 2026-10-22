"""SEO Writer — drafts an SEO article outline (title, headings, CTA).

Creative agent: LLM when keys are set, rule-based fallback otherwise.
Every outline ends with the honest Cyrus AI CTA. Draft goes to the
approval queue.
"""
import re

from agents.learn import get_lessons, log_run
from agents.llm import ask as llm_ask

NAME = "seo_writer"
CTA = "Plan it with Cyrus AI - CA$10 for 14 days of unlimited trip planning."


def _rule_based(topic, lessons):
    banned = " ".join(lessons.get("rejected_notes", [])).lower()
    title = f"{topic.title()}: The Complete 2026 Guide"
    if any(w in title.lower() for w in banned.split() if len(w) > 4):
        title = f"Everything About {topic.title()} (Honest Guide)"
    return {
        "title": title,
        "headings": [
            f"Where is {topic}?",
            f"Best time to visit {topic}",
            f"Top 5 things to do in {topic}",
            f"Where to stay near {topic}",
            f"How Cyrus AI plans your {topic} trip",
        ],
        "cta": CTA,
    }


def run(topic=None):
    lessons = get_lessons(NAME)
    topic = (topic or "best time to visit Victoria BC").strip()
    notes = lessons.get("rejected_notes", [])
    hint = ("Avoid these previously rejected angles: " + "; ".join(notes)
            if notes else "No past feedback yet.")

    prompt = (
        f"Draft an SEO article outline about: {topic}\n{hint}\n\n"
        "Format: line 1 = SEO title (<60 chars). Then exactly 5 H2 headings, "
        "each on its own line starting with '- '. No article body, just the outline. "
        "Honest, no clickbait, no fake facts."
    )
    text = llm_ask(prompt, system="You draft SEO outlines, no clickbait.",
                   max_tokens=300)
    mode = "llm"
    outline = None
    if text:
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        heads = [re.sub(r"^[-*]\s*", "", l) for l in lines[1:]
                 if l.startswith(("-", "*"))][:5]
        if lines and len(heads) >= 3:
            outline = {"title": lines[0][:80], "headings": heads, "cta": CTA}
    if not outline:
        outline = _rule_based(topic, lessons)
        mode = "rule-based"

    detail = (outline["title"] + "\n" +
              "\n".join("- " + h for h in outline["headings"]) +
              "\nCTA: " + CTA)
    run_id = log_run(NAME, f"SEO outline for '{topic}'", f"{mode}: {outline['title']}")
    return {
        "ok": True,
        "summary": f"SEO outline drafted for '{topic}' ({mode})",
        "details": {"outline": outline, "mode": mode, "run_id": run_id,
                    "lessons_seen": lessons["outcomes_seen"]},
        "proposed_approvals": [{
            "title": f"SEO outline: {outline['title'][:60]}",
            "kind": "content",
            "detail": detail,
        }],
    }
