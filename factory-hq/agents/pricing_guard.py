"""Pricing Guard — scans any text for prices and checks them all.

Deterministic checker (no LLM needed): stricter than Market Analyst - EVERY
dollar amount in the text must be a known real price from prices.json.
Unknown amounts (like the old $149) are flagged. Mismatches propose a fix.
"""
import json
import os
import re

from agents.learn import get_lessons, log_run

NAME = "pricing_guard"
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRICES_FILE = os.path.join(BASE, "prices.json")

DEFAULT_TEXT = (
    "Cyrus AI Tour Guide is CA$10 for 14 days. "  # correct
    "Old tours were $149 per person. "            # stale invented price
    "The app unlock is $5 one-time."             # correct
)


def _known_amounts():
    with open(PRICES_FILE, encoding="utf-8") as f:
        prices = json.load(f)
    amounts = set()
    for key, item in prices.items():
        if key == "note" or not isinstance(item, dict):
            continue
        m = re.search(r"\d+", item.get("price", ""))
        if m:
            amounts.add(m.group(0))
    return amounts, prices


def run(text=None):
    lessons = get_lessons(NAME)
    known, prices = _known_amounts()
    text = (text or DEFAULT_TEXT).strip()

    findings = []
    for m in re.finditer(r"(CA\$|\$)\s?(\d[\d,]*)", text):
        cur, amt = m.group(1), m.group(2).replace(",", "")
        ok = amt in known
        # extra honesty: the CA$10 chat price must keep its CA$
        if amt == "10" and cur == "$":
            ok = False
        findings.append({
            "check": "known_price", "ok": ok,
            "detail": f"found '{m.group(0)}' at char {m.start()} - "
                      + ("known real price" if ok else
                         "UNKNOWN/STALE price - not in prices.json"),
        })

    failed = [f for f in findings if not f["ok"]]
    run_id = log_run(NAME, f"scan {len(text)} chars for prices",
                     f"{len(findings) - len(failed)}/{len(findings)} known")
    proposed = []
    if failed:
        proposed.append({
            "title": "Pricing Guard: unknown/stale price in text",
            "kind": "quality",
            "detail": "Real prices: " + ", ".join(
                f"{v['product']} = {v['price']} ({v['term']})"
                for k, v in prices.items()
                if isinstance(v, dict)) + "\nFlagged: " + "; ".join(
                f["detail"] for f in failed),
        })
    return {
        "ok": not failed,
        "summary": (f"{len(findings) - len(failed)}/{len(findings)} prices are real"),
        "details": {"findings": findings, "run_id": run_id,
                    "lessons_seen": lessons["outcomes_seen"]},
        "proposed_approvals": proposed,
    }
