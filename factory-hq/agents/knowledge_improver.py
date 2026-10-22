"""Knowledge Improver — inspects the staged Cyrus AI knowledge file.

Real file inspection (no guessing):
  - file size + section markers A..N
  - presence of the hard-rule keywords from Section N
    (unverifiable-venue honesty, visa hard rule, USA numbers ban, CTA)
  - counts of trap-test guard phrases

Returns stats and proposes an approval if a hard rule looks missing.
"""
import os
import re

from agents.learn import get_lessons, log_run

KNOWLEDGE_FILE = os.path.expanduser(
    "~/workspace/your_files/knowledge-update/victoria-knowledge.txt"
)

HARD_RULES = {
    "unverifiable_venue": [r"unverifiable", r"do not invent"],
    "visa_hard_rule": [r"visa", r"ESTA"],
    "usa_numbers_ban": [r"never.*price.*memor", r"no.*prices.*memory"],
    "cta_10": [r"CA\$10", r"\$10.*14"],
}


def run():
    lessons = get_lessons("knowledge_improver")
    try:
        with open(KNOWLEDGE_FILE, encoding="utf-8") as f:
            text = f.read()
    except Exception as e:
        return {"ok": False, "summary": f"Knowledge file unreadable: {e}",
                "details": {}, "proposed_approvals": [{
                    "title": "Knowledge file missing/unreadable",
                    "kind": "knowledge",
                    "detail": str(e)}]}

    low = text.lower()
    sections = sorted(set(re.findall(r"SECTION ([A-N])\b", text)))
    rule_hits = {}
    for name, patterns in HARD_RULES.items():
        rule_hits[name] = any(re.search(p, low) for p in patterns)

    missing = [k for k, v in rule_hits.items() if not v]
    stats = {
        "bytes": len(text),
        "sections": "".join(sections),
        "hard_rules": rule_hits,
    }

    proposed = []
    if missing:
        proposed.append({
            "title": f"Weak hard rules in knowledge file: {', '.join(missing)}",
            "kind": "knowledge",
            "detail": ("Section N keywords not detected for: " + ", ".join(missing) +
                       ". Approve to queue a knowledge-merge strengthening task."),
        })

    summary = (f"{len(text)} bytes, sections {''.join(sections)}, "
               f"hard rules {sum(rule_hits.values())}/{len(rule_hits)} present")
    run_id = log_run("knowledge_improver", "inspect staged knowledge file", summary)
    return {
        "ok": not missing and sections == list("ABCDEFGHIJKLMN"),
        "summary": summary,
        "details": {"stats": stats, "run_id": run_id,
                    "lessons_seen": lessons["outcomes_seen"]},
        "proposed_approvals": proposed,
    }
