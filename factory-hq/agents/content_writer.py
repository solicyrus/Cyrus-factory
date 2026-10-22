"""Content Writer — drafts YouTube Shorts metadata packs.

Given a topic string, produces a paste-ready English title / description /
hashtags draft following the channel's proven format (hook title, Cyrus AI
CTA, victoriatourandadventure.com end-card line). The draft goes to the
factory approval queue — nothing is published without Cyrus's approve click.
"""
import re

CTA = "🌐 victoriatourandadventure.com"

BASE_TAGS = ["#VancouverIsland", "#BritishColumbia", "#ExploreBC",
             "#CanadaTravel", "#VictoriaBC"]


def _slug(topic):
    return re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")


def run(topic="hidden gem in Victoria BC"):
    topic = (topic or "hidden gem in Victoria BC").strip()
    title = f"{topic.title()} ✨ | Victoria, BC #shorts"
    description = (
        f"{topic.title()} — one more reason Victoria, BC is unforgettable 🇨🇦\n\n"
        f"Want the perfect itinerary? Let Cyrus AI plan it hour by hour 👇\n"
        f"{CTA}"
    )
    hashtags = " ".join(["#Shorts"] + BASE_TAGS)

    draft = {
        "title": title,
        "description": description,
        "hashtags": hashtags,
        "slug": _slug(topic),
    }
    return {
        "ok": True,
        "summary": f"Drafted Shorts pack for '{topic}'",
        "details": draft,
        "proposed_approvals": [{
            "title": f"Publish Shorts draft: {title[:60]}",
            "kind": "content",
            "detail": f"Title: {title}\nHashtags: {hashtags}\n(Approve = ready for Cyrus to upload from his phone)",
        }],
    }
