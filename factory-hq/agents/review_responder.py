"""Review Responder — drafts a short honest reply to a customer review.

Takes reviewer_name/rating/text. Rating-aware: warm thanks for 4-5 stars,
empathetic + invite to make it right for 1-3 stars. Never makes fake
promises, never invents refunds or bookings. The draft goes to the
approval queue - nothing is posted without Cyrus's approve click.
"""
from agents.learn import get_lessons, log_run

NAME = "review_responder"


def run(reviewer_name="Guest", rating=5, text=""):
    lessons = get_lessons(NAME)
    reviewer_name = (reviewer_name or "Guest").strip()
    text = (text or "").strip()
    try:
        rating = int(rating)
    except (TypeError, ValueError):
        rating = 5
    rating = max(1, min(5, rating))

    if rating >= 4:
        reply = (
            f"Thank you so much, {reviewer_name}! 🙏\n"
            "We're glad you enjoyed it. If you ever need a trip planned "
            "hour by hour, Cyrus AI is here to help - "
            "victoriatourandadventure.com"
        )
    elif rating == 3:
        reply = (
            f"Thank you for the honest feedback, {reviewer_name}.\n"
            "We'd love to do better - tell us what fell short and we'll "
            "make it right where we can."
        )
    else:
        reply = (
            f"{reviewer_name}, we're sorry to hear this.\n"
            "Please reach out at info@victoriatourandadventure.com with "
            "the details so we can look into it properly."
        )

    run_id = log_run(NAME, f"reply to {rating}-star review by {reviewer_name}",
                     reply[:70])
    return {
        "ok": True,
        "summary": f"Drafted reply to {reviewer_name}'s {rating}-star review",
        "details": {"reviewer_name": reviewer_name, "rating": rating,
                    "review_text": text[:200], "reply": reply,
                    "run_id": run_id,
                    "lessons_seen": lessons["outcomes_seen"]},
        "proposed_approvals": [{
            "title": f"Review reply draft for {reviewer_name}",
            "kind": "support",
            "detail": f"Original ({rating}★): {text[:200]}\n\nDraft reply:\n{reply}\n"
                      "(Approve = ready for Cyrus to post)",
        }],
    }
