"""Support Tone — checks a draft customer reply against tone rules.

Judgment agent: always runs deterministic rule checks (no fake promises,
honest prices, short). When the LLM backend is available it adds a second
opinion verdict. Failing replies produce a fix proposal in the approval queue.
"""
import re

from agents.learn import get_lessons, log_run
from agents.llm import ask as llm_ask

NAME = "support_tone"

BANNED = ["guarantee", "100%", "definitely", "definitively"]
KNOWN_PRICES = {"CA$10", "$5", "CA$5", "$79"}

DEFAULT_MESSAGE = "Hi, does the $10 plan cover my whole family for a month?"
DEFAULT_REPLY = ("Hi! The CA$10 plan is 14 days of unlimited trip planning. "
                 "Want me to start planning your trip?")


def _rule_checks(reply):
    findings = []
    low = reply.lower()
    bad = [w for w in BANNED if w in low]
    findings.append({"rule": "no_fake_promises",
                     "ok": not bad,
                     "detail": f"banned words found: {bad}" if bad else "no absolute promises"})
    words = len(reply.split())
    findings.append({"rule": "short", "ok": words <= 120,
                     "detail": f"{words} words (limit 120)"})
    prices = re.findall(r"(?:CA\$|\$)\d+", reply)
    unknown = [p for p in prices if p not in KNOWN_PRICES]
    findings.append({"rule": "honest_prices", "ok": not unknown,
                     "detail": f"prices: {prices or 'none'}"
                     + (f" - UNKNOWN: {unknown}" if unknown else "")})
    bookings = bool(re.search(r"\b(book|reserve) (it|your|a) (for|on)\b", low))
    findings.append({"rule": "no_fake_booking", "ok": not bookings,
                     "detail": "claims to book for the customer" if bookings
                     else "info-only, no booking claims"})
    return findings


def run(message=None, reply=None):
    lessons = get_lessons(NAME)
    message = (message or DEFAULT_MESSAGE).strip()
    reply = (reply or DEFAULT_REPLY).strip()

    findings = _rule_checks(reply)

    # Second opinion from the LLM when available
    notes = lessons.get("rejected_notes", [])
    hint = ("Past rejected replies were flagged for: " + "; ".join(notes)
            if notes else "")
    llm_text = llm_ask(
        "Customer message: " + message + "\nDraft reply: " + reply +
        f"\n{hint}\nIs this reply honest, short, with no fake promises, "
        "no invented prices and no booking claims? Answer PASS or FAIL "
        "plus one short line why.",
        system="You are a strict customer-support tone reviewer.",
        max_tokens=120)
    mode = "llm+rules" if llm_text else "rules"
    if llm_text:
        verdict = "FAIL" in llm_text.upper().split()[0]
        findings.append({"rule": "llm_second_opinion",
                         "ok": not verdict,
                         "detail": llm_text[:200]})

    failed = [f for f in findings if not f["ok"]]
    run_id = log_run(NAME, f"check reply to: {message[:80]}",
                     f"{mode}: {len(findings) - len(failed)}/{len(findings)} passed")
    proposed = []
    if failed:
        proposed.append({
            "title": "Support reply needs a fix (tone check failed)",
            "kind": "support",
            "detail": ("Customer: " + message + "\nDraft: " + reply +
                       "\nFailed: " + "; ".join(
                           f"{f['rule']}: {f['detail']}" for f in failed)),
        })
    return {
        "ok": not failed,
        "summary": (f"{len(findings) - len(failed)}/{len(findings)} tone checks passed ({mode})"),
        "details": {"findings": findings, "mode": mode, "run_id": run_id,
                    "lessons_seen": lessons["outcomes_seen"]},
        "proposed_approvals": proposed,
    }
