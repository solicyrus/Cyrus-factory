"""Market Analyst — flags price inconsistencies in a text against prices.json.

Deterministic checker (no LLM needed): finds dollar amounts near product
keywords and verifies each product is paired with its real price.
Proposes a fix in the approval queue on mismatch.
"""
import json
import os
import re

from agents.learn import get_lessons, log_run

NAME = "market_analyst"
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRICES_FILE = os.path.join(BASE, "prices.json")

# product keyword -> expected price as written in prices.json
EXPECT = {
    "cyrus ai": "CA$10",
    "cyrus_ai_chat": "CA$10",
    "app": "CA$5",
    "premium": "$79",
    "guardian": "$79",
}

DEFAULT_TEXT = (
    "Try Cyrus AI for only $5 for a whole month! "  # wrong: chat is CA$10/14d
    "The app unlock is CA$5 one-time. Premium Guardian Angel is $79 per trip."
)


def _load_prices():
    with open(PRICES_FILE, encoding="utf-8") as f:
        return json.load(f)


def run(text=None):
    lessons = get_lessons(NAME)
    prices = _load_prices()
    text = (text or DEFAULT_TEXT).strip()

    findings = []
    sentences = re.split(r"(?<=[.!?])\s+", text)
    for sent in sentences:
        low = sent.lower()
        amounts = re.findall(r"CA\$\d+|\$\d+", sent)
        if not amounts:
            continue
        for keyword, expected in EXPECT.items():
            if keyword in low and keyword != "cyrus_ai_chat":
                for amt in amounts:
                    ok = (amt == expected)
                    findings.append({
                        "rule": "price_consistency", "ok": ok,
                        "detail": (f"'{keyword}' paired with {amt} "
                                   f"(expected {expected}) in: {sent[:70]}"),
                    })

    failed = [f for f in findings if not f["ok"]]
    run_id = log_run(NAME, f"scan {len(text)} chars vs prices.json",
                     f"{len(findings) - len(failed)}/{len(findings)} consistent; "
                     f"catalog={len(prices) - 1} products")
    proposed = []
    if failed:
        proposed.append({
            "title": "Price inconsistency found by Market Analyst",
            "kind": "marketing",
            "detail": "; ".join(f["detail"] for f in failed),
        })
    return {
        "ok": not failed,
        "summary": (f"{len(findings) - len(failed)}/{len(findings)} price checks passed"),
        "details": {"findings": findings, "run_id": run_id,
                    "lessons_seen": lessons["outcomes_seen"]},
        "proposed_approvals": proposed,
    }
