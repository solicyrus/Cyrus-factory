"""Email Composer — drafts a short professional business email.

Takes to/subject/purpose. Builds a rule-based draft from a clean template,
then asks the LLM backend to polish it when keys are set (falls back to the
template otherwise). It only DRAFTS - it never sends anything. The draft
goes to the approval queue.
"""
import re

from agents.learn import get_lessons, log_run
from agents.llm import ask as llm_ask

NAME = "email_composer"


def _rule_based(to, subject, purpose):
    name = to.split("@")[0].replace(".", " ").title() if "@" in to else to
    body = (
        f"Hi {name},\n\n"
        f"{purpose.strip()}\n\n"
        "Please let me know if you have any questions.\n\n"
        "Best regards,\n"
        "Cyrus\n"
        "Victoria Tour and Adventure\n"
        "victoriatourandadventure.com"
    )
    return {"to": to, "subject": subject, "body": body}


def run(to="partner@example.com", subject="Hello", purpose=""):
    lessons = get_lessons(NAME)
    to = (to or "partner@example.com").strip()
    subject = (subject or "Hello").strip()
    purpose = (purpose or "Following up on our conversation.").strip()

    notes = lessons.get("rejected_notes", [])
    hint = ("Avoid these previously rejected styles: " + "; ".join(notes)
            if notes else "")
    prompt = (
        f"Polish this business email draft. Keep it short, professional, "
        f"honest, no hype. {hint}\n\n"
        f"To: {to}\nSubject: {subject}\n\n{purpose}\n\n"
        "Format exactly:\nSUBJECT: <subject line>\nBODY: <email body>"
    )
    text = llm_ask(prompt, system="You polish business emails.",
                   max_tokens=300)
    mode, draft = "llm", None
    if text:
        sub_m = re.search(r"SUBJECT:\s*(.+)", text)
        body_m = re.search(r"BODY:\s*(.+)", text, re.S)
        if sub_m and body_m:
            draft = {"to": to, "subject": sub_m.group(1).strip(),
                     "body": body_m.group(1).strip()}
    if not draft:
        draft = _rule_based(to, subject, purpose)
        mode = "rule-based"

    run_id = log_run(NAME, f"email to {to}: '{subject}'", f"{mode} draft")
    return {
        "ok": True,
        "summary": f"Drafted email to {to} ({mode})",
        "details": {**draft, "run_id": run_id,
                    "lessons_seen": lessons["outcomes_seen"]},
        "proposed_approvals": [{
            "title": f"Email draft: {draft['subject'][:60]}",
            "kind": "ops",
            "detail": (f"To: {draft['to']}\nSubject: {draft['subject']}\n\n"
                       f"{draft['body']}\n"
                       "(Approve = draft only - Cyrus sends it himself)"),
        }],
    }
