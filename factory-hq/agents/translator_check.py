"""Translator Check — verifies the 6-language closing lines file.

Deterministic checker (no LLM needed):
  1. All 6 language blocks (EN/FR/DE/ZH/FA/ES) present with their formal lines.
  2. Formality markers: ZH uses 您 (never 你), ES uses usted forms (never tu).
  3. The staged knowledge file mentions the CA$10 price (the closing lines
     themselves are closing questions; the price lives in the answer body).
"""
import os
import re

from agents.learn import get_lessons, log_run

NAME = "translator_check"
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLOSING_FILE = os.path.expanduser(
    "~/workspace/goals/victoria-ai-concierge-chatbot/hidden_files/"
    "closing-lines-6lang-2026-10-21.md")
KNOWLEDGE_FILE = os.path.expanduser(
    "~/workspace/your_files/knowledge-update/victoria-knowledge.txt")

LANGS = ["EN", "FR", "DE", "ZH", "FA", "ES"]


def run():
    lessons = get_lessons(NAME)
    findings = []

    try:
        with open(CLOSING_FILE, encoding="utf-8") as f:
            text = f.read()
    except Exception as e:
        run_id = log_run(NAME, "read closing-lines file", f"unreadable: {e}")
        return {"ok": False, "summary": f"Closing-lines file unreadable: {e}",
                "details": {"run_id": run_id}, "proposed_approvals": [{
                    "title": "Closing-lines file missing", "kind": "quality",
                    "detail": str(e)}]}

    for lang in LANGS:
        found = re.search(rf"- {lang}:", text) is not None
        findings.append({"rule": "language_present", "ok": found,
                         "detail": f"{lang} closing line {'present' if found else 'MISSING'}"})

    zh_block = re.search(r"- ZH: \"(.+?)\"", text)
    if zh_block:
        zh = zh_block.group(1)
        findings.append({"rule": "zh_formal", "ok": "您" in zh and "你" not in zh.replace("您", ""),
                         "detail": "ZH uses 您 (formal)" if "您" in zh else "ZH formal marker missing"})
    es_block = re.search(r"- ES: \"(.+?)\"", text)
    if es_block:
        es = es_block.group(1).lower()
        informal = re.search(r"\b(te|tu)\b", es) is not None
        findings.append({"rule": "es_formal", "ok": not informal and "gustar" in es,
                         "detail": "ES uses usted forms" if not informal else "ES informal forms found"})

    try:
        with open(KNOWLEDGE_FILE, encoding="utf-8") as f:
            kb = f.read()
        has_price = "CA$10" in kb or "CA\\$10" in kb
    except Exception:
        has_price = False
    findings.append({"rule": "price_in_knowledge", "ok": has_price,
                     "detail": "staged knowledge file mentions the CA$10 price"
                     if has_price else "CA$10 not found in staged knowledge file"})

    failed = [f for f in findings if not f["ok"]]
    run_id = log_run(NAME, "verify 6-language closing lines",
                     f"{len(findings) - len(failed)}/{len(findings)} passed")
    proposed = []
    if failed:
        proposed.append({
            "title": "Closing-lines check failed: " + ", ".join(f["rule"] for f in failed),
            "kind": "quality",
            "detail": "; ".join(f["detail"] for f in failed),
        })
    return {
        "ok": not failed,
        "summary": f"{len(findings) - len(failed)}/{len(findings)} translation checks passed",
        "details": {"findings": findings, "run_id": run_id,
                    "lessons_seen": lessons["outcomes_seen"]},
        "proposed_approvals": proposed,
    }
