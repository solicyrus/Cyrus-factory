"""Itinerary Checker — validates a trip itinerary for honesty traps.

Deterministic checker (no LLM needed). Takes any itinerary text and flags:
  1. invented prices: $ amounts not in the real prices.json catalog
  2. phone numbers: never invent these (Section N hard rule)
  3. definitive visa promises: "guaranteed visa", "will get your visa", etc.
  4. day-count mismatch: "3-day trip" header but 5 "Day N" sections
Pure logic - no guessing, every flag cites the exact text.
"""
import json
import os
import re

from agents.learn import get_lessons, log_run

NAME = "itinerary_checker"
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRICES_FILE = os.path.join(BASE, "prices.json")

PHONE_RE = re.compile(
    r"(?:\+\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}")
VISA_RE = re.compile(
    r"guaranteed visa|will get your visa|visa (is |will be )?(approved|certain|"
    r"assured)|100% visa|waiver guarantees|definitely get (a|the) visa",
    re.IGNORECASE)
PRICE_RE = re.compile(r"(CA\$|\$)\s?(\d[\d,]*)")
DAY_HEADER_RE = re.compile(r"(\d+)[- ]day (trip|itinerary|plan)", re.IGNORECASE)
DAY_SECTION_RE = re.compile(r"^#*\s*Day (\d+)\b", re.IGNORECASE | re.MULTILINE)

DEFAULT_TEXT = (
    "Your 3-day Victoria trip:\n"
    "Day 1: Butchart Gardens ($149 entry).\n"
    "Day 2: Whale watching, call +1 250 590-1234 to book.\n"
    "Day 3: Royal BC Museum.\n"
    "Day 4: Extra day in Tofino.\n"
    "Day 5: Departure. You will get your visa easily!"
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
    return amounts


def run(text=None):
    lessons = get_lessons(NAME)
    text = (text or DEFAULT_TEXT).strip()
    known = _known_amounts()
    findings = []

    # 1. invented prices
    for m in PRICE_RE.finditer(text):
        cur, amt = m.group(1), m.group(2).replace(",", "")
        ok = amt in known and not (amt == "10" and cur == "$")
        findings.append({
            "check": "price", "ok": ok,
            "detail": f"'{m.group(0)}' - "
                      + ("real price" if ok else "INVENTED/STALE price"),
        })

    # 2. phone numbers
    for m in PHONE_RE.finditer(text):
        findings.append({
            "check": "phone", "ok": False,
            "detail": f"'{m.group(0)}' - phone numbers must never come from memory",
        })

    # 3. definitive visa promises
    for m in VISA_RE.finditer(text):
        findings.append({
            "check": "visa_claim", "ok": False,
            "detail": f"'{m.group(0)}' - definitive visa promise, forbidden",
        })

    # 4. day-count mismatch
    header = DAY_HEADER_RE.search(text)
    days = sorted({int(d) for d in DAY_SECTION_RE.findall(text)})
    if header and days:
        promised, planned = int(header.group(1)), max(days)
        ok = promised == planned
        findings.append({
            "check": "day_count", "ok": ok,
            "detail": f"header says {promised}-day, "
                      f"{planned} day sections found"
                      + ("" if ok else " - MISMATCH"),
        })

    failed = [f for f in findings if not f["ok"]]
    run_id = log_run(NAME, f"validate {len(text)} chars of itinerary",
                     f"{len(failed)} honesty flags")
    proposed = []
    if failed:
        proposed.append({
            "title": f"Itinerary Checker: {len(failed)} honesty flags",
            "kind": "quality",
            "detail": "\n".join(
                f"- [{f['check']}] {f['detail']}" for f in failed),
        })
    return {
        "ok": not failed,
        "summary": (f"{len(findings) - len(failed)}/{len(findings)} checks clean"
                    if findings else "no checkable claims found"),
        "details": {"findings": findings, "run_id": run_id,
                    "lessons_seen": lessons["outcomes_seen"]},
        "proposed_approvals": proposed,
    }
